from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CreateProcurementRequest(BaseModel):
    request: str = Field(min_length=10, max_length=2000)


class WorkflowSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    current_stage: str
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None


class RequestSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    original_request: str
    normalized_requirements: dict[str, Any]
    status: str
    company_name: str
    company_location: str
    created_at: datetime
    updated_at: datetime
    workflow: WorkflowSummary


class TaskView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    agent_type: str
    task_type: str
    status: str
    dependencies: list[str]
    retry_count: int
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None


class EventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    task_id: str | None
    agent: str
    event_type: str
    capability: str | None
    provider: str | None
    status: str
    duration_ms: int | None
    metadata_json: dict[str, Any]
    timestamp: datetime


class ProductView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    manufacturer: str | None
    model: str | None
    specifications: dict[str, Any]
    unit_price: Decimal | None
    currency: str | None
    available_quantity: int | None
    availability: str | None
    warranty: str | None
    delivery: str | None
    source_url: str
    verification_status: str


class SupplierView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    website: str
    location: str | None
    supplier_type: str | None
    verification_status: str
    products: list[ProductView]


class RecommendationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    selected_options: list[dict[str, Any]]
    evaluation_results: list[dict[str, Any]]
    total_cost: Decimal | None
    currency: str | None
    reasoning_summary: str
    evidence_references: list[str]
    status: str
    review_note: str | None


class ReviewRecommendation(BaseModel):
    decision: str = Field(pattern="^(approved|rejected)$")
    note: str | None = Field(default=None, max_length=1000)


class RequestDetail(RequestSummary):
    suppliers: list[SupplierView] = []
    recommendation: RecommendationView | None = None


class ExecutionView(BaseModel):
    workflow: WorkflowSummary
    tasks: list[TaskView]
    events: list[EventView]
