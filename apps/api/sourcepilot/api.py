from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from sourcepilot.config import Settings, get_settings
from sourcepilot.db import get_session
from sourcepilot.repositories import ProcurementRepository, WorkflowRepository
from sourcepilot.schemas import (
    CompanyContextView,
    CreateProcurementRequest,
    ExecutionView,
    RecommendationView,
    RequestDetail,
    RequestSummary,
    ReviewRecommendation,
    SupplierView,
)
from sourcepilot.services import ProcurementService

router = APIRouter(prefix="/api/v1")
Session = Annotated[AsyncSession, Depends(get_session)]
Config = Annotated[Settings, Depends(get_settings)]


@router.get("/context", response_model=CompanyContextView)
async def get_company_context(config: Config):
    return {
        "company_name": config.company_name,
        "company_location": config.company_location,
        "country": config.company_country,
        "currency": config.default_currency,
        "procurement_region": config.procurement_region,
        "sourcing_regions": config.sourcing_regions,
    }


@router.post("/requests", response_model=RequestSummary, status_code=status.HTTP_202_ACCEPTED)
async def create_request(
    payload: CreateProcurementRequest, request: Request, db: Session, config: Config
):
    enqueue = getattr(request.app.state, "enqueue", None)
    return await ProcurementService(db, config, enqueue).create(payload.request)


@router.get("/requests", response_model=list[RequestSummary])
async def list_requests(db: Session):
    return await ProcurementRepository(db).list()


@router.get("/requests/{request_id}", response_model=RequestDetail)
async def get_request(request_id: str, db: Session):
    repository = ProcurementRepository(db)
    procurement = await repository.get(request_id)
    if procurement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "procurement request not found")
    view = RequestSummary.model_validate(procurement).model_dump()
    view["suppliers"] = await repository.suppliers(request_id)
    view["recommendation"] = await repository.recommendation(request_id)
    return view


@router.get("/requests/{request_id}/suppliers", response_model=list[SupplierView])
async def get_suppliers(request_id: str, db: Session):
    return await ProcurementRepository(db).suppliers(request_id)


@router.get("/requests/{request_id}/recommendation", response_model=RecommendationView)
async def get_recommendation(request_id: str, db: Session):
    recommendation = await ProcurementRepository(db).recommendation(request_id)
    if recommendation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "recommendation is not ready")
    return recommendation


@router.post("/requests/{request_id}/recommendation/review", response_model=RecommendationView)
async def review_recommendation(
    request_id: str, payload: ReviewRecommendation, db: Session, config: Config
):
    try:
        result = await ProcurementService(db, config).review(
            request_id, payload.decision, payload.note
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "recommendation is not ready")
    return result


@router.get("/workflows/{workflow_id}", response_model=ExecutionView)
async def get_workflow(workflow_id: str, db: Session):
    workflow = await WorkflowRepository(db).get(workflow_id)
    if workflow is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "workflow not found")
    return {"workflow": workflow, "tasks": workflow.tasks, "events": workflow.events}
