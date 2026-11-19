"""
Pydantic schemas for operational analytics, cycle time, waiting time,
rework, bottlenecks, vendor/department performance, and trends.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Overview ──────────────────────────────────────────────────────────────────

class OverviewMetrics(BaseModel):
    dataset_id: uuid.UUID
    total_purchase_cases: int
    total_events: int
    completed_cases: int
    incomplete_cases: int
    completion_rate: float
    avg_cycle_time_hours: float
    median_cycle_time_hours: float
    p90_cycle_time_hours: float
    rework_cases: int
    rework_percentage: float
    sla_hours: float
    sla_breach_cases: int
    sla_breach_percentage: float
    total_spend_usd: float
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


# ── Cycle Time ────────────────────────────────────────────────────────────────

class CycleTimeDistributionBin(BaseModel):
    bin_start_hours: float
    bin_end_hours: float
    case_count: int


class CycleTimeMetrics(BaseModel):
    dataset_id: uuid.UUID
    total_cases: int
    completed_cases: int
    avg_cycle_time_hours: float
    median_cycle_time_hours: float
    p75_cycle_time_hours: float
    p90_cycle_time_hours: float
    p95_cycle_time_hours: float
    min_cycle_time_hours: float
    max_cycle_time_hours: float
    sla_hours: float
    sla_breach_count: int
    sla_breach_percentage: float
    distribution: List[CycleTimeDistributionBin]


# ── Waiting Time & Processing Time ────────────────────────────────────────────

class ActivityTimeMetric(BaseModel):
    activity: str
    transition_count: int
    avg_waiting_time_hours: float
    median_waiting_time_hours: float
    p90_waiting_time_hours: float
    min_waiting_time_hours: float
    max_waiting_time_hours: float
    total_waiting_time_hours: float


class WaitingTimeMetrics(BaseModel):
    dataset_id: uuid.UUID
    overall_avg_waiting_time_hours: float
    activities: List[ActivityTimeMetric]


# ── Rework ────────────────────────────────────────────────────────────────────

class ActivityReworkMetric(BaseModel):
    activity: str
    rework_case_count: int
    total_rework_occurrences: int
    rework_rate: float
    max_repetitions_in_case: int


class ReworkMetrics(BaseModel):
    dataset_id: uuid.UUID
    total_cases: int
    cases_with_rework: int
    rework_case_percentage: float
    total_rework_events: int
    activities: List[ActivityReworkMetric]


# ── Bottlenecks ───────────────────────────────────────────────────────────────

class BottleneckItem(BaseModel):
    rank: int
    activity: str
    bottleneck_score: float
    avg_waiting_time_hours: float
    median_waiting_time_hours: float
    rework_rate: float
    sla_breach_rate: float
    transition_count: int
    affected_case_count: int = 0
    reasons: List[str]


class BottlenecksResponse(BaseModel):
    dataset_id: uuid.UUID
    top_bottleneck: Optional[str]
    ranking_methodology: str
    bottlenecks: List[BottleneckItem]


# ── Vendor & Department Performance ───────────────────────────────────────────

class VendorPerformanceItem(BaseModel):
    vendor_id: str
    total_cases: int
    total_spend_usd: float
    avg_cycle_time_hours: float
    median_cycle_time_hours: float
    sla_breach_count: int
    sla_breach_rate: float
    completed_cases: int
    completion_rate: float


class VendorPerformanceResponse(BaseModel):
    dataset_id: uuid.UUID
    total_vendors: int
    vendors: List[VendorPerformanceItem]


class DepartmentPerformanceItem(BaseModel):
    department: str
    total_cases: int
    total_spend_usd: float
    avg_cycle_time_hours: float
    rework_cases: int
    rework_rate: float
    completed_cases: int
    completion_rate: float


class DepartmentPerformanceResponse(BaseModel):
    dataset_id: uuid.UUID
    total_departments: int
    departments: List[DepartmentPerformanceItem]


# ── Trends ────────────────────────────────────────────────────────────────────

class MonthlyTrendItem(BaseModel):
    month: str  # YYYY-MM
    case_volume: int
    completed_cases: int
    total_events: int
    total_spend_usd: float
    avg_cycle_time_hours: float
    sla_breach_rate: float


class TrendsResponse(BaseModel):
    dataset_id: uuid.UUID
    trends: List[MonthlyTrendItem]
