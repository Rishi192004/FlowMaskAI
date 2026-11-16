"""
Operational Analytics API Endpoints.
Provides overview, cycle time, waiting time, rework, bottlenecks,
vendor/department performance, and monthly trend metrics.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.service import (
    get_bottleneck_analytics,
    get_cycle_time_analytics,
    get_department_performance_analytics,
    get_overview_analytics,
    get_rework_analytics,
    get_trends_analytics,
    get_vendor_performance_analytics,
    get_waiting_time_analytics,
)
from app.db.session import get_db
from app.schemas.analytics import (
    BottlenecksResponse,
    CycleTimeMetrics,
    DepartmentPerformanceResponse,
    OverviewMetrics,
    ReworkMetrics,
    TrendsResponse,
    VendorPerformanceResponse,
    WaitingTimeMetrics,
)

router = APIRouter(prefix="/analytics", tags=["Operational Analytics"])


@router.get(
    "/overview",
    response_model=OverviewMetrics,
    summary="Get operational overview metrics",
    description="Returns case volume, completion rates, cycle time stats, rework rates, and SLA breaches.",
)
def get_overview(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None, description="Filter events after or on this timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter events before or on this timestamp"),
    sla_hours: float = Query(720.0, ge=1.0, description="Process SLA threshold in hours (default 30 days / 720h)"),
    db: Session = Depends(get_db),
) -> OverviewMetrics:
    return get_overview_analytics(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
        sla_hours=sla_hours,
    )


@router.get(
    "/cycle-time",
    response_model=CycleTimeMetrics,
    summary="Get cycle time distribution and percentiles",
    description="Calculates average, median, P75, P90, P95 cycle times, SLA breach counts, and histogram distribution bins.",
)
def get_cycle_time(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    sla_hours: float = Query(720.0, ge=1.0),
    db: Session = Depends(get_db),
) -> CycleTimeMetrics:
    return get_cycle_time_analytics(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
        sla_hours=sla_hours,
    )


@router.get(
    "/waiting-time",
    response_model=WaitingTimeMetrics,
    summary="Get activity queueing and waiting times",
    description="Calculates transition waiting times between consecutive activities across all cases.",
)
def get_waiting_time(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
) -> WaitingTimeMetrics:
    return get_waiting_time_analytics(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/rework",
    response_model=ReworkMetrics,
    summary="Get rework and repetition metrics",
    description="Identifies repeated activities within cases according to execution frequency rules.",
)
def get_rework(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
) -> ReworkMetrics:
    return get_rework_analytics(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/bottlenecks",
    response_model=BottlenecksResponse,
    summary="Identify and rank operational bottlenecks",
    description="Ranks bottlenecks using explainable metrics (waiting times, rework rates, SLA breach rates).",
)
def get_bottlenecks(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    activity_sla_hours: float = Query(48.0, ge=1.0, description="Activity SLA threshold in hours"),
    db: Session = Depends(get_db),
) -> BottlenecksResponse:
    return get_bottleneck_analytics(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
        activity_sla_hours=activity_sla_hours,
    )


@router.get(
    "/vendor-performance",
    response_model=VendorPerformanceResponse,
    summary="Get vendor-wise performance analytics",
    description="Analyzes cycle time, spend, completion rate, and SLA compliance across all vendors.",
)
def get_vendor_performance(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    sla_hours: float = Query(720.0, ge=1.0),
    db: Session = Depends(get_db),
) -> VendorPerformanceResponse:
    return get_vendor_performance_analytics(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
        sla_hours=sla_hours,
    )


@router.get(
    "/department-performance",
    response_model=DepartmentPerformanceResponse,
    summary="Get department-wise performance analytics",
    description="Analyzes spend, cycle times, rework rates, and completion rates by requesting department.",
)
def get_department_performance(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
) -> DepartmentPerformanceResponse:
    return get_department_performance_analytics(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/trends",
    response_model=TrendsResponse,
    summary="Get monthly transaction and efficiency trends",
    description="Tracks monthly case volume, completed cases, spend, cycle time, and SLA breach trends.",
)
def get_trends(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    sla_hours: float = Query(720.0, ge=1.0),
    db: Session = Depends(get_db),
) -> TrendsResponse:
    return get_trends_analytics(
        db=db,
        dataset_id=dataset_id,
        sla_hours=sla_hours,
    )
