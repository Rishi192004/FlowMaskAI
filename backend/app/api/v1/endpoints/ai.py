"""
AI & Grounded Recommendations API Endpoints.
Connects calculated metrics from ETL, analytics, process mining, and conformance
to the 8-rule prescriptive recommendation engine.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.ai.engine import generate_recommendations
from app.db.session import get_db
from app.schemas.ai import RecommendationsConfig, RecommendationsResponse

router = APIRouter(prefix="/ai", tags=["AI & Recommendations"])


@router.get(
    "/recommendations",
    response_model=RecommendationsResponse,
    summary="Generate grounded process optimization recommendations",
    description=(
        "Executes 8 configurable business rules against actual computed process metrics. "
        "Every recommendation links to verified case counts, supporting metrics, and evidence."
    ),
)
def get_recommendations(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None, description="Optional start datetime filter"),
    end_date: Optional[datetime] = Query(None, description="Optional end datetime filter"),
    skip_approval_threshold: float = Query(0.0, ge=0.0, le=1.0, description="Skipped approval rate threshold"),
    early_invoice_threshold: float = Query(0.0, ge=0.0, le=1.0, description="Early invoice rate threshold"),
    skip_verification_threshold: float = Query(0.0, ge=0.0, le=1.0, description="Skipped invoice verification threshold"),
    high_rework_threshold: float = Query(0.08, ge=0.0, le=1.0, description="Rework rate threshold"),
    approval_bottleneck_hours: float = Query(24.0, ge=1.0, description="Manager approval wait time threshold in hours"),
    low_fpy_threshold: float = Query(0.80, ge=0.0, le=1.0, description="First Pass Yield target threshold"),
    high_abandonment_threshold: float = Query(0.05, ge=0.0, le=1.0, description="Case abandonment rate threshold"),
    sla_breach_threshold: float = Query(0.10, ge=0.0, le=1.0, description="SLA breach rate threshold"),
    sla_hours: float = Query(720.0, ge=1.0, description="SLA duration threshold in hours"),
    db: Session = Depends(get_db),
) -> RecommendationsResponse:
    config = RecommendationsConfig(
        skip_approval_threshold=skip_approval_threshold,
        early_invoice_threshold=early_invoice_threshold,
        skip_verification_threshold=skip_verification_threshold,
        high_rework_threshold=high_rework_threshold,
        approval_bottleneck_hours=approval_bottleneck_hours,
        low_fpy_threshold=low_fpy_threshold,
        high_abandonment_threshold=high_abandonment_threshold,
        sla_breach_threshold=sla_breach_threshold,
        sla_hours=sla_hours,
    )
    return generate_recommendations(
        db=db,
        dataset_id=dataset_id,
        config=config,
        start_date=start_date,
        end_date=end_date,
    )
