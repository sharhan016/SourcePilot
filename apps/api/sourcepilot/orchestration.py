import asyncio
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from sourcepilot.agents import (
    EvaluationAgent,
    RecommendationAgent,
    ResearchAgent,
    VerificationAgent,
)
from sourcepilot.capabilities import CapabilityExecutor, ExecutionPolicy, WebSearchCapability
from sourcepilot.config import Settings
from sourcepilot.domain import TaskStatus, VerificationStatus, WorkflowStatus
from sourcepilot.models import (
    Evidence,
    ExecutionEvent,
    ProcurementRequest,
    Product,
    Recommendation,
    Supplier,
    Workflow,
    WorkflowTask,
    uuid4,
)
from sourcepilot.providers.llm import build_openai, build_openrouter
from sourcepilot.providers.search import (
    ExaSearchProvider,
    FirecrawlSearchProvider,
    SearchProviderRouter,
)
from sourcepilot.providers.types import ProductCandidate


def utcnow() -> datetime:
    return datetime.now(UTC)


def dependencies_satisfied(task: WorkflowTask, tasks: list[WorkflowTask]) -> bool:
    statuses = {candidate.id: candidate.status for candidate in tasks}
    return all(statuses.get(dependency) == TaskStatus.COMPLETED for dependency in task.dependencies)


class Orchestrator:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings,
        *,
        search_provider=None,
        llm_provider=None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.search_provider_override = search_provider
        self.llm_provider_override = llm_provider
        self.pending_events: list[dict[str, Any]] = []
        self.current_task_id: str | None = None
        self.workflow_id: str | None = None

    async def run(self, workflow_id: str) -> None:
        self.workflow_id = workflow_id
        async with self.session_factory() as session:
            workflow = await self._load_workflow(session, workflow_id)
            if workflow is None or workflow.status in (
                WorkflowStatus.COMPLETED,
                WorkflowStatus.CANCELLED,
            ):
                return
            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = workflow.started_at or utcnow()
            workflow.error = None
            await session.commit()
            try:
                candidates: list[ProductCandidate] = []
                verification: dict[str, str] = {}
                corroboration: dict[str, list[str]] = {}
                evaluations: list[dict[str, Any]] = []
                for task in workflow.tasks:
                    if task.status == TaskStatus.COMPLETED:
                        continue
                    if not dependencies_satisfied(task, workflow.tasks):
                        task.status = TaskStatus.WAITING
                        workflow.status = WorkflowStatus.WAITING
                        await session.commit()
                        return
                    workflow.current_stage = task.agent_type
                    await self._start_task(session, task)
                    if task.agent_type == "research":
                        candidates = await self._research(workflow.request)
                        await self._persist_candidates(session, workflow.request, candidates)
                        output = {"candidates": len(candidates)}
                    elif task.agent_type == "verification":
                        candidates = candidates or await self._candidate_snapshot(
                            session, workflow.request.id
                        )
                        verification, corroboration = await self._verify(candidates)
                        await self._persist_verification(
                            session, workflow.request, verification, corroboration
                        )
                        output = {
                            "verified": sum(value == "verified" for value in verification.values())
                        }
                    elif task.agent_type == "evaluation":
                        candidates = candidates or await self._candidate_snapshot(
                            session, workflow.request.id
                        )
                        if not verification:
                            verification = {
                                str(item.source_url): "verified"
                                if item.is_first_party
                                else "extracted"
                                for item in candidates
                            }
                        evaluations = EvaluationAgent().evaluate(
                            candidates,
                            verification,
                            workflow.request.normalized_requirements["quantity"],
                            workflow.request.normalized_requirements.get(
                                "currency", self.settings.default_currency
                            ),
                        )
                        output = {"compared": len(evaluations)}
                    else:
                        if not evaluations:
                            evaluations = await self._evaluation_snapshot(
                                session, workflow.request.id
                            )
                        await self._recommend(session, workflow.request, evaluations)
                        output = {"recommendation": "ready"}
                    await self._complete_task(session, task, output)
                workflow.status = WorkflowStatus.COMPLETED
                workflow.current_stage = "review"
                workflow.completed_at = utcnow()
                workflow.request.status = WorkflowStatus.COMPLETED
                await self._flush_events(session)
                await session.commit()
            except Exception as exc:
                await session.rollback()
                workflow = await self._load_workflow(session, workflow_id)
                if workflow:
                    workflow.status = WorkflowStatus.FAILED
                    workflow.error = f"{type(exc).__name__}: {exc}"[:1000]
                    workflow.request.status = WorkflowStatus.FAILED
                    if self.current_task_id:
                        task = next(
                            (item for item in workflow.tasks if item.id == self.current_task_id),
                            None,
                        )
                        if task:
                            task.status = TaskStatus.FAILED
                            task.error = workflow.error
                    await self._flush_events(session)
                    await session.commit()

    async def _providers(self):
        import httpx

        timeout = httpx.Timeout(self.settings.provider_timeout_seconds)
        client = httpx.AsyncClient(timeout=timeout, follow_redirects=True)
        if self.search_provider_override and self.llm_provider_override:
            return self.search_provider_override, self.llm_provider_override, client
        exa = ExaSearchProvider(self.settings.exa_api_key, client)
        firecrawl = FirecrawlSearchProvider(self.settings.firecrawl_api_key, client)
        search = (
            SearchProviderRouter(firecrawl, [exa])
            if self.settings.search_provider == "firecrawl"
            else SearchProviderRouter(exa, [firecrawl])
        )
        llm = (
            build_openrouter(self.settings.llm_model, self.settings.openrouter_api_key, client)
            if self.settings.llm_provider == "openrouter"
            else build_openai(self.settings.llm_model, self.settings.openai_api_key, client)
        )
        return self.search_provider_override or search, self.llm_provider_override or llm, client

    async def _capabilities(self):
        search_provider, llm_provider, client = await self._providers()
        executor = CapabilityExecutor(
            ExecutionPolicy(
                timeout_seconds=self.settings.provider_timeout_seconds,
                max_retries=self.settings.provider_max_retries,
            ),
            self.settings.max_concurrent_tools,
            self._capture_event,
        )
        return WebSearchCapability(search_provider, executor), llm_provider, client

    async def _research(self, request: ProcurementRequest) -> list[ProductCandidate]:
        search, llm, client = await self._capabilities()
        requirements = dict(request.normalized_requirements)
        requirements.setdefault("currency", self.settings.default_currency)
        requirements.setdefault("delivery_location", request.company_location)
        requirements.setdefault("procurement_region", self.settings.procurement_region)
        requirements.setdefault("sourcing_regions", self.settings.sourcing_regions)
        try:
            return await ResearchAgent(search, llm, self.settings.research_max_rounds).run(
                requirements
            )
        finally:
            await client.aclose()

    async def _verify(
        self, candidates: list[ProductCandidate]
    ) -> tuple[dict[str, str], dict[str, list[str]]]:
        search, _, client = await self._capabilities()
        agent = VerificationAgent(search)
        try:
            results = await asyncio.gather(
                *(agent.verify(candidate) for candidate in candidates), return_exceptions=True
            )
        finally:
            await client.aclose()
        verification: dict[str, str] = {}
        corroboration: dict[str, list[str]] = {}
        for candidate, result in zip(candidates, results, strict=True):
            key = str(candidate.source_url)
            verification[key] = "unavailable" if isinstance(result, Exception) else result[0]
            corroboration[key] = [] if isinstance(result, Exception) else result[1]
        return verification, corroboration

    async def _capture_event(self, event: dict[str, Any]) -> None:
        self.pending_events.append(event)

    async def _flush_events(self, session: AsyncSession) -> None:
        if not self.workflow_id:
            return
        for event in self.pending_events:
            session.add(
                ExecutionEvent(
                    workflow_id=self.workflow_id,
                    task_id=self.current_task_id,
                    agent="orchestrator",
                    event_type="capability_invocation",
                    capability=event.get("capability"),
                    provider=event.get("provider"),
                    status=event["status"],
                    duration_ms=event.get("duration_ms"),
                    metadata_json={
                        key: value
                        for key, value in event.items()
                        if key not in {"capability", "provider", "status", "duration_ms"}
                    },
                )
            )
        self.pending_events.clear()

    async def _start_task(self, session: AsyncSession, task: WorkflowTask) -> None:
        self.current_task_id = task.id
        task.status = TaskStatus.RUNNING
        task.started_at = utcnow()
        session.add(
            ExecutionEvent(
                workflow_id=task.workflow_id,
                task_id=task.id,
                agent=task.agent_type,
                event_type="task_started",
                status="running",
            )
        )
        await session.commit()

    async def _complete_task(
        self, session: AsyncSession, task: WorkflowTask, output: dict[str, Any]
    ) -> None:
        await self._flush_events(session)
        task.status = TaskStatus.COMPLETED
        task.completed_at = utcnow()
        task.output_reference = output
        session.add(
            ExecutionEvent(
                workflow_id=task.workflow_id,
                task_id=task.id,
                agent=task.agent_type,
                event_type="task_completed",
                status="completed",
                metadata_json=output,
            )
        )
        await session.commit()

    async def _persist_candidates(
        self, session: AsyncSession, request: ProcurementRequest, candidates: list[ProductCandidate]
    ) -> None:
        suppliers: dict[str, Supplier] = {}
        for candidate in candidates:
            key = str(candidate.supplier_website)
            supplier = suppliers.get(key)
            if supplier is None:
                supplier = Supplier(
                    id=uuid4(),
                    procurement_request_id=request.id,
                    name=candidate.supplier_name,
                    website=key,
                    location=candidate.supplier_location,
                    supplier_type=candidate.supplier_type,
                )
                suppliers[key] = supplier
                session.add(supplier)
            product = Product(
                id=uuid4(),
                supplier=supplier,
                name=candidate.product_name,
                manufacturer=candidate.manufacturer,
                model=candidate.model,
                specifications=candidate.specifications,
                unit_price=candidate.unit_price,
                currency=candidate.currency,
                available_quantity=candidate.available_quantity,
                availability=candidate.availability,
                warranty=candidate.warranty,
                delivery=candidate.delivery,
                source_url=str(candidate.source_url),
            )
            session.add(product)
            session.add(
                Evidence(
                    id=uuid4(),
                    procurement_request_id=request.id,
                    supplier_id=supplier.id,
                    product=product,
                    source_url=str(candidate.source_url),
                    source_type=candidate.source_type,
                    claim={
                        "unit_price": str(candidate.unit_price) if candidate.unit_price else None,
                        "availability": candidate.availability,
                        "warranty": candidate.warranty,
                    },
                    classification="first_party" if candidate.is_first_party else "third_party",
                    verification_status=VerificationStatus.EXTRACTED,
                )
            )
        await session.flush()

    async def _persist_verification(
        self,
        session: AsyncSession,
        request: ProcurementRequest,
        verification: dict[str, str],
        corroboration: dict[str, list[str]],
    ) -> None:
        suppliers = (
            (
                await session.execute(
                    select(Supplier)
                    .where(Supplier.procurement_request_id == request.id)
                    .options(selectinload(Supplier.products))
                )
            )
            .scalars()
            .all()
        )
        for supplier in suppliers:
            product_statuses: list[str] = []
            for product in supplier.products:
                status = verification.get(product.source_url, VerificationStatus.UNAVAILABLE)
                product.verification_status = status
                product_statuses.append(status)
                for source_url in corroboration.get(product.source_url, []):
                    session.add(
                        Evidence(
                            id=uuid4(),
                            procurement_request_id=request.id,
                            supplier_id=supplier.id,
                            product_id=product.id,
                            source_url=source_url,
                            source_type="verification_search",
                            claim={"corroborates_product": product.name},
                            classification=(
                                "first_party"
                                if urlparse(source_url).hostname
                                == urlparse(supplier.website).hostname
                                else "third_party"
                            ),
                            verification_status=status,
                        )
                    )
            supplier.verification_status = (
                VerificationStatus.VERIFIED
                if VerificationStatus.VERIFIED in product_statuses
                else VerificationStatus.EXTRACTED
            )

    async def _candidate_snapshot(
        self, session: AsyncSession, request_id: str
    ) -> list[ProductCandidate]:
        suppliers = (
            (
                await session.execute(
                    select(Supplier)
                    .where(Supplier.procurement_request_id == request_id)
                    .options(selectinload(Supplier.products))
                )
            )
            .scalars()
            .all()
        )
        return [
            ProductCandidate(
                supplier_name=supplier.name,
                supplier_website=supplier.website,
                supplier_location=supplier.location,
                supplier_type=supplier.supplier_type,
                product_name=product.name,
                manufacturer=product.manufacturer,
                model=product.model,
                specifications=product.specifications,
                unit_price=product.unit_price,
                currency=product.currency,
                available_quantity=product.available_quantity,
                availability=product.availability,
                warranty=product.warranty,
                delivery=product.delivery,
                source_url=product.source_url,
                is_first_party=urlparse(product.source_url).hostname
                == urlparse(supplier.website).hostname,
            )
            for supplier in suppliers
            for product in supplier.products
        ]

    async def _evaluation_snapshot(
        self, session: AsyncSession, request_id: str
    ) -> list[dict[str, Any]]:
        candidates = await self._candidate_snapshot(session, request_id)
        products = (
            await session.execute(
                select(Product).join(Supplier).where(Supplier.procurement_request_id == request_id)
            )
        ).scalars()
        verification = {product.source_url: product.verification_status for product in products}
        request = await session.get(ProcurementRequest, request_id)
        return EvaluationAgent().evaluate(
            candidates,
            verification,
            request.normalized_requirements["quantity"],
            request.normalized_requirements.get("currency", self.settings.default_currency),
        )

    async def _recommend(
        self, session: AsyncSession, request: ProcurementRequest, evaluations: list[dict[str, Any]]
    ) -> None:
        result = RecommendationAgent().build(
            evaluations, request.normalized_requirements["quantity"]
        )
        selected = result["selected"]
        total = (
            Decimal(selected[0]["total_cost"]) if selected and selected[0]["total_cost"] else None
        )
        session.add(
            Recommendation(
                procurement_request_id=request.id,
                selected_options=selected,
                evaluation_results=evaluations,
                total_cost=total,
                currency=selected[0]["currency"] if selected else None,
                reasoning_summary=result["summary"],
                evidence_references=[item["source_url"] for item in result["shortlist"]],
            )
        )

    async def _load_workflow(self, session: AsyncSession, workflow_id: str) -> Workflow | None:
        result = await session.execute(
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .options(selectinload(Workflow.request), selectinload(Workflow.tasks))
        )
        workflow = result.scalar_one_or_none()
        if workflow:
            workflow.tasks.sort(key=lambda task: task.created_at)
        return workflow
