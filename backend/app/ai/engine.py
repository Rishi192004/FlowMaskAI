"""
Core Recommendations Engine.
Orchestrates rule evaluation against calculated operational metrics,
ranks recommendations by estimated impact, and generates audit reports.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.orm import Session

from app.ai.rules import (
    evaluate_approval_bottleneck,
    evaluate_early_invoice,
    evaluate_high_abandonment,
    evaluate_high_rework,
    evaluate_low_fpy,
    evaluate_skip_approval,
    evaluate_skip_verification,
    evaluate_sla_breach,
)
from app.analytics.service import (
    get_bottleneck_analytics,
    get_overview_analytics,
    get_rework_analytics,
)
from app.conformance.engine import get_conformance_overview_response
from app.core.exceptions import NotFoundError
from app.models.dataset import Dataset
from app.schemas.ai import (
    RecommendationItem,
    RecommendationsConfig,
    RecommendationsResponse,
)


def generate_recommendations(
    db: Session,
    dataset_id: uuid.UUID,
    config: Optional[RecommendationsConfig] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> RecommendationsResponse:
    """
    Executes all 8 recommendation rules against the active dataset.
    Every finding is strictly derived from actual computed process data.
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise NotFoundError(f"Dataset '{dataset_id}' not found.")

    active_config = config or RecommendationsConfig()

    # 1. Gather all required analytical foundations
    overview = get_overview_analytics(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
        sla_hours=active_config.sla_hours,
    )

    conformance = get_conformance_overview_response(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
    )

    bottlenecks = get_bottleneck_analytics(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
        activity_sla_hours=active_config.approval_bottleneck_hours,
    )

    rework = get_rework_analytics(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
    )

    # 2. Evaluate all 8 recommendation rules
    rules_to_run = [
        evaluate_skip_approval(conformance, overview, active_config),
        evaluate_early_invoice(conformance, overview, active_config),
        evaluate_skip_verification(conformance, overview, active_config),
        evaluate_high_rework(overview, rework, active_config),
        evaluate_approval_bottleneck(bottlenecks, overview, active_config),
        evaluate_low_fpy(conformance, overview, active_config),
        evaluate_high_abandonment(overview, active_config),
        evaluate_sla_breach(overview, active_config),
    ]

    # 3. Filter triggered recommendations
    triggered: List[RecommendationItem] = [r for r in rules_to_run if r is not None]

    # 4. Sort descending by impact score
    triggered.sort(key=lambda r: r.estimated_impact_score, reverse=True)

    # 5. Severity distribution count
    crit_count = sum(1 for r in triggered if r.severity == "CRITICAL")
    high_count = sum(1 for r in triggered if r.severity == "HIGH")
    med_count = sum(1 for r in triggered if r.severity == "MEDIUM")
    low_count = sum(1 for r in triggered if r.severity == "LOW")

    return RecommendationsResponse(
        dataset_id=dataset_id,
        total_cases_analyzed=overview.total_purchase_cases,
        recommendations_count=len(triggered),
        critical_count=crit_count,
        high_count=high_count,
        medium_count=med_count,
        low_count=low_count,
        recommendations=triggered,
        rules_evaluated_count=len(rules_to_run),
        evaluation_timestamp=datetime.now(timezone.utc),
        active_config=active_config,
    )
