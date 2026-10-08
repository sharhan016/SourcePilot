import re
from collections.abc import Callable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from sourcepilot.config import Settings
from sourcepilot.domain import STAGE_ORDER, AgentType, RecommendationStatus
from sourcepilot.models import ProcurementRequest, Workflow, WorkflowTask, uuid4
from sourcepilot.repositories import ProcurementRepository


def normalize_requirements(text: str) -> dict[str, Any]:
    """Conservative deterministic baseline; the research agent may enrich it later."""
    quantity_match = re.search(r"\b(\d+)\b", text)
    quantity = int(quantity_match.group(1)) if quantity_match else 1
    lowered = text.lower()
    category = "laptop" if any(word in lowered for word in ("laptop", "macbook")) else "general"
    return {"quantity": quantity, "category": category, "description": text.strip()}


class ProcurementService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        enqueue: Callable[[str], None] | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.enqueue = enqueue
        self.requests = ProcurementRepository(session)

    async def create(self, original_request: str) -> ProcurementRequest:
        requirements = normalize_requirements(original_request)
        requirements.update(
            {
                "currency": self.settings.default_currency,
                "delivery_location": self.settings.company_location,
                "procurement_region": self.settings.procurement_region,
                "sourcing_regions": self.settings.sourcing_regions,
            }
        )
        procurement = ProcurementRequest(
            id=uuid4(),
            company_name=self.settings.company_name,
            company_location=self.settings.company_location,
            original_request=original_request,
            normalized_requirements=requirements,
        )
        workflow = Workflow(id=uuid4(), request=procurement)
        previous: list[str] = []
        for stage in STAGE_ORDER:
            task = WorkflowTask(
                id=uuid4(),
                workflow=workflow,
                agent_type=AgentType(stage).value,
                task_type=f"{stage}_procurement",
                dependencies=list(previous),
                input_reference={"request_id": procurement.id},
            )
            previous = [task.id]
        await self.requests.add(procurement)
        await self.session.commit()
        if self.enqueue:
            self.enqueue(workflow.id)
        return await self.requests.get(procurement.id)  # type: ignore[return-value]

    async def review(self, request_id: str, decision: str, note: str | None) -> Any:
        recommendation = await self.requests.recommendation(request_id)
        if recommendation is None:
            return None
        if recommendation.status != RecommendationStatus.READY:
            raise ValueError("recommendation has already been reviewed")
        recommendation.status = decision
        recommendation.review_note = note
        await self.session.commit()
        return recommendation
