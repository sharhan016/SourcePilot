import asyncio
import logging

from sqlalchemy import select

from sourcepilot.config import get_settings
from sourcepilot.db import SessionFactory
from sourcepilot.domain import WorkflowStatus
from sourcepilot.models import Workflow
from sourcepilot.orchestration import Orchestrator

logger = logging.getLogger("sourcepilot.worker")


class DatabaseWorker:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.semaphore = asyncio.Semaphore(self.settings.max_concurrent_workflows)
        self.running: set[str] = set()

    async def recover(self) -> None:
        async with SessionFactory() as session:
            workflows = (
                await session.execute(
                    select(Workflow).where(Workflow.status == WorkflowStatus.RUNNING)
                )
            ).scalars()
            for workflow in workflows:
                workflow.status = WorkflowStatus.WAITING
                workflow.error = (
                    "Recovered after worker interruption; completed tasks are preserved."
                )
            await session.commit()

    async def claim(self) -> list[str]:
        async with SessionFactory() as session:
            rows = await session.execute(
                select(Workflow.id)
                .where(Workflow.status.in_([WorkflowStatus.QUEUED, WorkflowStatus.WAITING]))
                .order_by(Workflow.created_at)
                .limit(self.settings.max_concurrent_workflows)
            )
            return [
                workflow_id for workflow_id in rows.scalars() if workflow_id not in self.running
            ]

    async def execute(self, workflow_id: str) -> None:
        async with self.semaphore:
            self.running.add(workflow_id)
            try:
                await Orchestrator(SessionFactory, self.settings).run(workflow_id)
            finally:
                self.running.discard(workflow_id)

    async def run_forever(self) -> None:
        await self.recover()
        while True:
            for workflow_id in await self.claim():
                asyncio.create_task(self.execute(workflow_id))
            await asyncio.sleep(2)


async def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    await DatabaseWorker().run_forever()


if __name__ == "__main__":
    asyncio.run(main())
