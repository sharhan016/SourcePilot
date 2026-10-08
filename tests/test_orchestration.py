import asyncio
from decimal import Decimal

import httpx
import pytest
from sourcepilot.agents import CandidateBatch
from sourcepilot.capabilities import CapabilityExecutor, ExecutionPolicy
from sourcepilot.config import Settings
from sourcepilot.db import Base
from sourcepilot.domain import TaskStatus, WorkflowStatus
from sourcepilot.models import Evidence, Recommendation, Workflow
from sourcepilot.orchestration import Orchestrator, dependencies_satisfied
from sourcepilot.providers.types import ProductCandidate, SearchDocument
from sourcepilot.services import ProcurementService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


class RecordingSearchProvider:
    name = "recording-search"

    def __init__(self) -> None:
        self.active = 0
        self.peak = 0

    async def search(self, query: str, limit: int = 8) -> list[SearchDocument]:
        self.active += 1
        self.peak = max(self.peak, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        if query.startswith('"'):
            supplier = query.split('"')[3]
            host = supplier.lower().replace(" ", "") + ".example"
            return [
                SearchDocument(
                    title="First-party corroboration",
                    url=f"https://{host}/business-terms",
                    content="Warranty and stock confirmed",
                    provider=self.name,
                ),
                SearchDocument(
                    title="Independent listing",
                    url=f"https://directory.example/{host}",
                    content="Authorized supplier",
                    provider=self.name,
                ),
            ]
        return [
            SearchDocument(
                title=f"Supplier {index}",
                url=f"https://supplier{index}.example/product",
                content=(
                    f"Supplier {index} lists MacBook Pro 14-inch in stock for INR "
                    f"{150000 + index * 1000}"
                ),
                provider=self.name,
            )
            for index in range(3)
        ]


class ExtractingLLM:
    name = "test-llm"
    model = "test"

    async def structured_output(self, messages, output_type):
        payload = messages[-1].content
        index = next(number for number in range(3) if f"supplier{number}.example" in payload)
        return CandidateBatch(
            candidates=[
                ProductCandidate(
                    supplier_name=f"Supplier {index}",
                    supplier_website=f"https://supplier{index}.example",
                    product_name="MacBook Pro 14-inch",
                    manufacturer="Apple",
                    model="M-series",
                    unit_price=Decimal(150000 + index * 1000),
                    currency="INR",
                    available_quantity=75,
                    availability="In stock",
                    warranty="One year",
                    delivery="7 days",
                    source_url=f"https://supplier{index}.example/product",
                    is_first_party=True,
                )
            ]
        )


@pytest.mark.asyncio
async def test_capability_retries_are_bounded_and_observable() -> None:
    attempts = 0
    events = []

    async def operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise httpx.ConnectError("temporary")
        return "done"

    async def capture(event):
        events.append(event)

    executor = CapabilityExecutor(
        ExecutionPolicy(timeout_seconds=1, max_retries=2, base_backoff_seconds=0), 1, capture
    )
    assert (
        await executor.call(
            capability="web_search", provider="test", cache_key="x", operation=operation
        )
        == "done"
    )
    assert attempts == 3
    assert [event["status"] for event in events] == ["retrying", "retrying", "completed"]


@pytest.mark.asyncio
async def test_workflow_runs_agents_persists_result_and_parallelizes_verification(tmp_path) -> None:
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'workflow.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    settings = Settings(max_concurrent_tools=3, research_max_rounds=1)
    async with factory() as session:
        procurement = await ProcurementService(session, settings).create(
            "Find 50 MacBook Pro 14-inch laptops for the company"
        )
        workflow_id = procurement.workflow.id

    search = RecordingSearchProvider()
    await Orchestrator(factory, settings, search_provider=search, llm_provider=ExtractingLLM()).run(
        workflow_id
    )

    async with factory() as session:
        workflow = await session.get(Workflow, workflow_id)
        recommendation = (
            await session.execute(
                select(Recommendation).where(
                    Recommendation.procurement_request_id == procurement.id
                )
            )
        ).scalar_one()
        evidence_count = len((await session.execute(select(Evidence))).scalars().all())
        assert workflow.status == WorkflowStatus.COMPLETED
        assert recommendation.status == "ready"
        assert recommendation.total_cost == Decimal("7500000.00")
        assert recommendation.evidence_references
        assert evidence_count >= 6  # extracted claims plus independent verification sources
    assert search.peak >= 2
    await engine.dispose()


def test_task_dependencies_require_completed_predecessors() -> None:
    predecessor = type("Task", (), {"id": "a", "status": TaskStatus.RUNNING})()
    task = type("Task", (), {"dependencies": ["a"]})()
    assert not dependencies_satisfied(task, [predecessor])
    predecessor.status = TaskStatus.COMPLETED
    assert dependencies_satisfied(task, [predecessor])
