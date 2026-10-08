import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from sourcepilot.db import Base
from sourcepilot.domain import (
    RecommendationStatus,
    TaskStatus,
    VerificationStatus,
    WorkflowStatus,
)


def uuid4() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(UTC)


class ProcurementRequest(Base):
    __tablename__ = "procurement_requests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    company_name: Mapped[str] = mapped_column(String(200))
    company_location: Mapped[str] = mapped_column(String(200))
    original_request: Mapped[str] = mapped_column(Text)
    normalized_requirements: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default=WorkflowStatus.QUEUED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    workflow: Mapped["Workflow"] = relationship(back_populates="request", uselist=False)


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    procurement_request_id: Mapped[str] = mapped_column(
        ForeignKey("procurement_requests.id", ondelete="CASCADE"), unique=True
    )
    status: Mapped[str] = mapped_column(String(30), default=WorkflowStatus.QUEUED)
    current_stage: Mapped[str] = mapped_column(String(50), default="queued")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    request: Mapped[ProcurementRequest] = relationship(back_populates="workflow")
    tasks: Mapped[list["WorkflowTask"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )
    events: Mapped[list["ExecutionEvent"]] = relationship(
        back_populates="workflow", cascade="all, delete-orphan"
    )


class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"))
    agent_type: Mapped[str] = mapped_column(String(40))
    task_type: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default=TaskStatus.QUEUED)
    dependencies: Mapped[list[str]] = mapped_column(JSON, default=list)
    input_reference: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    output_reference: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    retry_count: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    workflow: Mapped[Workflow] = relationship(back_populates="tasks")


class Supplier(Base):
    __tablename__ = "suppliers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    procurement_request_id: Mapped[str] = mapped_column(
        ForeignKey("procurement_requests.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(250))
    website: Mapped[str] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(250))
    supplier_type: Mapped[str | None] = mapped_column(String(80))
    contact_info: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    verification_status: Mapped[str] = mapped_column(
        String(30), default=VerificationStatus.DISCOVERED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    products: Mapped[list["Product"]] = relationship(
        back_populates="supplier", cascade="all, delete-orphan"
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    supplier_id: Mapped[str] = mapped_column(ForeignKey("suppliers.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(300))
    manufacturer: Mapped[str | None] = mapped_column(String(160))
    model: Mapped[str | None] = mapped_column(String(200))
    specifications: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    available_quantity: Mapped[int | None]
    availability: Mapped[str | None] = mapped_column(String(160))
    warranty: Mapped[str | None] = mapped_column(Text)
    delivery: Mapped[str | None] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(
        String(30), default=VerificationStatus.EXTRACTED
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    supplier: Mapped[Supplier] = relationship(back_populates="products")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="product")


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    procurement_request_id: Mapped[str] = mapped_column(
        ForeignKey("procurement_requests.id", ondelete="CASCADE")
    )
    supplier_id: Mapped[str | None] = mapped_column(ForeignKey("suppliers.id"))
    product_id: Mapped[str | None] = mapped_column(ForeignKey("products.id"))
    source_url: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(String(60))
    claim: Mapped[dict[str, Any]] = mapped_column(JSON)
    classification: Mapped[str] = mapped_column(String(30))
    verification_status: Mapped[str] = mapped_column(
        String(30), default=VerificationStatus.DISCOVERED
    )
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    product: Mapped[Product | None] = relationship(back_populates="evidence")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    procurement_request_id: Mapped[str] = mapped_column(
        ForeignKey("procurement_requests.id", ondelete="CASCADE"), unique=True
    )
    selected_options: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    evaluation_results: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    reasoning_summary: Mapped[str] = mapped_column(Text)
    evidence_references: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default=RecommendationStatus.READY)
    review_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class ExecutionEvent(Base):
    __tablename__ = "execution_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uuid4)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"))
    task_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_tasks.id"))
    agent: Mapped[str] = mapped_column(String(50))
    event_type: Mapped[str] = mapped_column(String(80))
    capability: Mapped[str | None] = mapped_column(String(80))
    provider: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30))
    duration_ms: Mapped[int | None]
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    workflow: Mapped[Workflow] = relationship(back_populates="events")
