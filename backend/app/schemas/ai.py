"""
Pydantic schemas for Grounded Recommendations Engine and Decision Support.
Ensures 100% data grounding and parameterization from computed process metrics.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class RecommendationCategoryEnum(str, Enum):
    COMPLIANCE = "COMPLIANCE"
    FINANCIAL_RISK = "FINANCIAL_RISK"
    QUALITY = "QUALITY"
    EFFICIENCY = "EFFICIENCY"


class RecommendationSeverityEnum(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RecommendationItem(BaseModel):
    recommendation_id: str = Field(
        ..., description="Unique recommendation ID, e.g. REC-SKIP-APPROVAL-001"
    )
    category: str = Field(
        ..., description="Business category: Compliance, Financial Risk, Quality, or Efficiency"
    )
    severity: str = Field(
        ..., description="Severity level: CRITICAL, HIGH, MEDIUM, LOW"
    )
    business_problem: str = Field(
        ..., description="Business problem description identifying the operational breakdown"
    )
    supporting_metric: str = Field(
        ..., description="Name of the exact computed metric backing this finding"
    )
    actual_metric_value: float = Field(
        ..., description="Calculated metric value derived from database event records"
    )
    threshold_or_baseline: str = Field(
        ..., description="Benchmark threshold or comparison baseline"
    )
    affected_case_count: int = Field(
        ..., description="Exact number of purchase cases impacted"
    )
    affected_case_percentage: float = Field(
        ..., description="Percentage of total cases impacted"
    )
    estimated_operational_impact: str = Field(
        ..., description="Quantified operational delay, capital exposure, or audit risk"
    )
    recommended_corrective_action: str = Field(
        ..., description="Actionable operational and systems corrective measure"
    )
    evidence_and_explanation: str = Field(
        ..., description="Verifiable explanation and audit evidence from real records"
    )
    rule_id: str = Field(
        ..., description="Internal rule catalogue code"
    )
    estimated_impact_score: float = Field(
        ..., description="Numeric ranking score (severity weight * volume exposure)"
    )


class RecommendationsConfig(BaseModel):
    """
    Configurable baselines and thresholds for all 8 recommendation rules.
    Allows independent testing and policy customization.
    """
    skip_approval_threshold: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Trigger threshold for skipped approvals (zero-tolerance default: > 0.0)"
    )
    early_invoice_threshold: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Trigger threshold for invoice before goods receipt (default: > 0.0)"
    )
    skip_verification_threshold: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Trigger threshold for payment without invoice verification (default: > 0.0)"
    )
    high_rework_threshold: float = Field(
        default=0.08, ge=0.0, le=1.0, description="Trigger threshold for case rework rate (default: 8.0%)"
    )
    approval_bottleneck_hours: float = Field(
        default=24.0, ge=1.0, description="Trigger threshold for Manager Approval average wait (default: 24.0 hours)"
    )
    low_fpy_threshold: float = Field(
        default=0.80, ge=0.0, le=1.0, description="Trigger threshold for First Pass Yield (default: < 80.0%)"
    )
    high_abandonment_threshold: float = Field(
        default=0.05, ge=0.0, le=1.0, description="Trigger threshold for case abandonment / incomplete rate (default: 5.0%)"
    )
    sla_breach_threshold: float = Field(
        default=0.10, ge=0.0, le=1.0, description="Trigger threshold for SLA breach rate (default: 10.0%)"
    )
    sla_hours: float = Field(
        default=720.0, ge=1.0, description="Contractual P2P cycle time SLA threshold in hours (default: 720.0h / 30 days)"
    )


class RecommendationsResponse(BaseModel):
    dataset_id: uuid.UUID
    total_cases_analyzed: int
    recommendations_count: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    recommendations: List[RecommendationItem]
    rules_evaluated_count: int
    evaluation_timestamp: datetime
    active_config: RecommendationsConfig
