from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from sourcepilot.models import (
    ExecutionEvent,
    ProcurementRequest,
    Recommendation,
    Supplier,
    Workflow,
)


class ProcurementRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(self, request: ProcurementRequest) -> ProcurementRequest:
        self.session.add(request)
        await self.session.flush()
        return request

    async def list(self) -> list[ProcurementRequest]:
        result = await self.session.execute(
            select(ProcurementRequest)
            .options(selectinload(ProcurementRequest.workflow))
            .order_by(ProcurementRequest.created_at.desc())
        )
        return list(result.scalars())

    async def get(self, request_id: str) -> ProcurementRequest | None:
        result = await self.session.execute(
            select(ProcurementRequest)
            .where(ProcurementRequest.id == request_id)
            .options(selectinload(ProcurementRequest.workflow))
        )
        return result.scalar_one_or_none()

    async def suppliers(self, request_id: str) -> list[Supplier]:
        result = await self.session.execute(
            select(Supplier)
            .where(Supplier.procurement_request_id == request_id)
            .options(selectinload(Supplier.products))
        )
        return list(result.scalars())

    async def recommendation(self, request_id: str) -> Recommendation | None:
        result = await self.session.execute(
            select(Recommendation).where(Recommendation.procurement_request_id == request_id)
        )
        return result.scalar_one_or_none()


class WorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, workflow_id: str) -> Workflow | None:
        result = await self.session.execute(
            select(Workflow)
            .where(Workflow.id == workflow_id)
            .options(selectinload(Workflow.tasks), selectinload(Workflow.events))
        )
        return result.scalar_one_or_none()

    async def events(self, workflow_id: str) -> list[ExecutionEvent]:
        result = await self.session.execute(
            select(ExecutionEvent)
            .where(ExecutionEvent.workflow_id == workflow_id)
            .order_by(ExecutionEvent.timestamp)
        )
        return list(result.scalars())
