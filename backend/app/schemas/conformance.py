"""
Pydantic schemas for Conformance Checking, Deviation Detection,
Case-level Audits, and Configurable Business Rules.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Configurable Business Rules ───────────────────────────────────────────────

class ConformanceRulesConfig(BaseModel):
    reference_sequence: List[str] = Field(
        default=[
            "Purchase Requisition",
            "Manager Approval",
            "Purchase Order Created",
            "Goods Received",
            "Invoice Received",
            "Invoice Verified",
            "Payment Completed",
        ],
        description="Standard ordered activities for the reference workflow",
    )
    require_manager_approval: bool = Field(
        default=True,
        description="If True, flagging cases where Manager Approval is skipped before PO creation",
    )
    prohibit_early_invoice_verification: bool = Field(
        default=True,
        description="If True, flagging cases where Invoice Verified occurs before Goods Received",
    )
    allow_repeated_approval: bool = Field(
        default=False,
        description="If False, flagging repeated Manager Approval events as rework deviations",
    )
    require_payment_completion: bool = Field(
        default=True,
        description="If True, flagging cases that terminate without Payment Completed as incomplete",
    )
    prohibit_unexpected_activities: bool = Field(
        default=True,
        description="If True, flagging activities outside the reference model",
    )
    strict_sequence: bool = Field(
        default=True,
        description="If True, enforces strict chronological sequence of activities",
    )


# ── Deviation Specifics ───────────────────────────────────────────────────────

class CaseDeviationDetail(BaseModel):
    deviation_type: str  # "SKIPPED_APPROVAL", "EARLY_INVOICE_VERIFICATION", "REPEATED_APPROVAL", "UNEXPECTED_ACTIVITY", "OUT_OF_ORDER", "INCOMPLETE_PROCESS"
    severity: str        # "HIGH", "MEDIUM", "LOW"
    description: str     # Human-readable explanation of what went wrong
    culprit_activity: str
    culprit_event_id: Optional[int] = None
    culprit_timestamp: Optional[datetime] = None
    expected: str        # Expected activity or condition
    actual: str          # Observed state or sequence


class CaseDeviationItem(BaseModel):
    case_id: str
    is_conformant: bool
    fitness_score: float
    total_events: int
    duration_hours: float
    deviations: List[CaseDeviationDetail]


class CaseDeviationsListResponse(BaseModel):
    dataset_id: uuid.UUID
    total_cases: int
    conformant_cases_count: int
    deviant_cases_count: int
    page: int
    page_size: int
    pages: int
    cases: List[CaseDeviationItem]


# ── Deviation Type Frequency Breakdown ────────────────────────────────────────

class DeviationSummaryItem(BaseModel):
    deviation_type: str
    category: str       # "Compliance", "Risk", "Quality", "Efficiency"
    severity: str       # "HIGH", "MEDIUM", "LOW"
    affected_cases: int
    percentage_of_cases: float
    description: str


class ConformanceOverviewResponse(BaseModel):
    dataset_id: uuid.UUID
    total_cases: int
    conformant_cases: int
    deviant_cases: int
    conformance_percentage: float
    average_fitness_score: float
    deviation_breakdown: List[DeviationSummaryItem]
    active_rules: ConformanceRulesConfig
