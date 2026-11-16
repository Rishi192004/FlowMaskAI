"""
Conformance Checking & Deviation Detection API Endpoints.
Provides overview fitness metrics, deviation breakdown, case-level root cause drill-down,
and administrative configuration of expected business rules.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.conformance.engine import (
    get_case_deviations_response,
    get_conformance_overview_response,
)
from app.conformance.rules import get_conformance_rules, update_conformance_rules
from app.db.session import get_db
from app.schemas.conformance import (
    CaseDeviationsListResponse,
    ConformanceOverviewResponse,
    ConformanceRulesConfig,
    DeviationSummaryItem,
)

router = APIRouter(prefix="/conformance", tags=["Conformance Checking"])


@router.get(
    "/overview",
    response_model=ConformanceOverviewResponse,
    summary="Get conformance overview and fitness score",
    description="Returns conformance percentage, token replay fitness score, and deviation frequency breakdown.",
)
def get_overview(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
) -> ConformanceOverviewResponse:
    return get_conformance_overview_response(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/deviations",
    response_model=List[DeviationSummaryItem],
    summary="Get deviation frequency breakdown",
    description="Lists all detected deviation types, severity, category, and affected case counts.",
)
def get_deviations(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    db: Session = Depends(get_db),
) -> List[DeviationSummaryItem]:
    overview = get_conformance_overview_response(db=db, dataset_id=dataset_id)
    return overview.deviation_breakdown


@router.get(
    "/cases",
    response_model=CaseDeviationsListResponse,
    summary="Get case-level deviation audit",
    description="Lists cases with exact culprit events, violation descriptions, and fitness scores.",
)
def get_cases(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    filter_deviant_only: bool = Query(False, description="If True, returns only cases that have deviations"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> CaseDeviationsListResponse:
    return get_case_deviations_response(
        db=db,
        dataset_id=dataset_id,
        filter_deviant_only=filter_deviant_only,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/rules",
    response_model=ConformanceRulesConfig,
    summary="Get active conformance rules",
    description="Returns the reference process sequence and configurable business validation rules.",
)
def get_rules(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
) -> ConformanceRulesConfig:
    return get_conformance_rules(dataset_id=dataset_id)


@router.put(
    "/rules",
    response_model=ConformanceRulesConfig,
    summary="Update active conformance rules",
    description="Allows administrators to configure expected process constraints and threshold policies.",
)
def update_rules(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    config: ConformanceRulesConfig = ...,
) -> ConformanceRulesConfig:
    return update_conformance_rules(dataset_id=dataset_id, new_config=config)
