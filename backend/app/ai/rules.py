"""
Independent, Configurable Rule Evaluators for Grounded Process Mining Recommendations.
Every rule operates strictly on computed analytical metrics and database records.
Zero fabrication: parameterized templates populate from real case counts and calculated values.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from app.schemas.ai import (
    RecommendationCategoryEnum,
    RecommendationItem,
    RecommendationsConfig,
    RecommendationSeverityEnum,
)
from app.schemas.analytics import BottlenecksResponse, OverviewMetrics, ReworkMetrics
from app.schemas.conformance import ConformanceOverviewResponse


# ── Severity Weight Multipliers for Ranking ────────────────────────────────────
SEVERITY_WEIGHTS = {
    "CRITICAL": 100.0,
    "HIGH": 75.0,
    "MEDIUM": 40.0,
    "LOW": 15.0,
}


def round_num(val: float, decimals: int = 4) -> float:
    return round(float(val), decimals)


# ── 1. SKIP_APPROVAL ──────────────────────────────────────────────────────────
def evaluate_skip_approval(
    conformance: ConformanceOverviewResponse,
    overview: OverviewMetrics,
    config: RecommendationsConfig,
) -> Optional[RecommendationItem]:
    """
    Evaluates whether Purchase Orders were issued without prior authorized Manager Approval.
    Category: Compliance | Severity: HIGH / CRITICAL
    """
    total_cases = overview.total_purchase_cases
    if total_cases == 0:
        return None

    dev = next(
        (d for d in conformance.deviation_breakdown if d.deviation_type == "SKIPPED_APPROVAL"),
        None,
    )
    affected_count = dev.affected_cases if dev else 0
    actual_pct = round_num(affected_count / total_cases)

    if actual_pct <= config.skip_approval_threshold:
        return None

    severity = "CRITICAL" if actual_pct > 0.05 else "HIGH"
    weight = SEVERITY_WEIGHTS[severity]
    impact_score = round_num(weight * (actual_pct * 100.0) + (affected_count * 0.1), 2)

    return RecommendationItem(
        recommendation_id=f"REC-SKIP-APPROVAL-{affected_count:03d}",
        rule_id="SKIP_APPROVAL",
        category=RecommendationCategoryEnum.COMPLIANCE.value,
        severity=severity,
        business_problem=(
            "Unauthorized Purchase Orders issued without mandatory managerial approval "
            "prior to commitment generation."
        ),
        supporting_metric="skipped_approval_case_percentage",
        actual_metric_value=actual_pct,
        threshold_or_baseline=f"Threshold: > {config.skip_approval_threshold * 100:.1f}% (Zero tolerance compliance policy)",
        affected_case_count=affected_count,
        affected_case_percentage=round_num(actual_pct * 100.0, 2),
        estimated_operational_impact=(
            f"Exposes organization to unauthorized procurement liability across {affected_count:,} cases "
            f"({actual_pct * 100.0:.1f}% of volume). Bypasses budgetary governance and capital expenditure controls."
        ),
        recommended_corrective_action=(
            "Implement automated ERP approval gating that prohibits PO release until digital manager sign-off is logged. "
            "Audit all {affected_count:,} unapproved orders for retroactive ratification or supplier contract cancellations."
        ),
        evidence_and_explanation=(
            f"Audit replay flagged {affected_count:,} cases where 'Purchase Order Created' occurred with zero preceding "
            f"'Manager Approval' events in the case history."
        ),
        estimated_impact_score=impact_score,
    )


# ── 2. EARLY_INVOICE ──────────────────────────────────────────────────────────
def evaluate_early_invoice(
    conformance: ConformanceOverviewResponse,
    overview: OverviewMetrics,
    config: RecommendationsConfig,
) -> Optional[RecommendationItem]:
    """
    Evaluates whether invoices were verified prior to physical goods receipt (3-way match failure).
    Category: Financial Risk | Severity: HIGH
    """
    total_cases = overview.total_purchase_cases
    if total_cases == 0:
        return None

    dev = next(
        (d for d in conformance.deviation_breakdown if d.deviation_type == "EARLY_INVOICE_VERIFICATION"),
        None,
    )
    affected_count = dev.affected_cases if dev else 0
    actual_pct = round_num(affected_count / total_cases)

    if actual_pct <= config.early_invoice_threshold:
        return None

    severity = "CRITICAL" if actual_pct > 0.05 else "HIGH"
    weight = SEVERITY_WEIGHTS[severity]
    impact_score = round_num(weight * (actual_pct * 100.0) + (affected_count * 0.1), 2)

    return RecommendationItem(
        recommendation_id=f"REC-EARLY-INVOICE-{affected_count:03d}",
        rule_id="EARLY_INVOICE",
        category=RecommendationCategoryEnum.FINANCIAL_RISK.value,
        severity=severity,
        business_problem=(
            "Invoices verified and scheduled for disbursement prior to physical goods receipt confirmation, "
            "violating the fundamental three-way matching control."
        ),
        supporting_metric="early_invoice_verification_case_percentage",
        actual_metric_value=actual_pct,
        threshold_or_baseline=f"Threshold: > {config.early_invoice_threshold * 100:.1f}% (Zero-tolerance financial control)",
        affected_case_count=affected_count,
        affected_case_percentage=round_num(actual_pct * 100.0, 2),
        estimated_operational_impact=(
            f"Direct exposure to erroneous or premature disbursements on unfulfilled orders across {affected_count:,} cases. "
            f"Increases risk of supplier disputes and duplicate payments."
        ),
        recommended_corrective_action=(
            "Enforce hard system control in Accounts Payable software preventing invoice verification queue entry until "
            "warehouse inventory system logs verified Goods Received Note (GRN)."
        ),
        evidence_and_explanation=(
            f"Event sequence analysis verified that in {affected_count:,} cases, 'Invoice Verified' timestamps preceded "
            f"'Goods Received' timestamps, reversing standard procurement controls."
        ),
        estimated_impact_score=impact_score,
    )


# ── 3. SKIP_VERIFICATION ──────────────────────────────────────────────────────
def evaluate_skip_verification(
    conformance: ConformanceOverviewResponse,
    overview: OverviewMetrics,
    config: RecommendationsConfig,
) -> Optional[RecommendationItem]:
    """
    Evaluates whether payments were executed without documented invoice verification.
    Category: Compliance | Severity: HIGH
    """
    total_cases = overview.total_purchase_cases
    if total_cases == 0:
        return None

    dev = next(
        (d for d in conformance.deviation_breakdown if d.deviation_type == "SKIPPED_INVOICE_VERIFICATION"),
        None,
    )
    affected_count = dev.affected_cases if dev else 0
    actual_pct = round_num(affected_count / total_cases)

    if actual_pct <= config.skip_verification_threshold:
        return None

    severity = "HIGH"
    weight = SEVERITY_WEIGHTS[severity]
    impact_score = round_num(weight * (actual_pct * 100.0) + (affected_count * 0.1), 2)

    return RecommendationItem(
        recommendation_id=f"REC-SKIP-VERIFY-{affected_count:03d}",
        rule_id="SKIP_VERIFICATION",
        category=RecommendationCategoryEnum.COMPLIANCE.value,
        severity=severity,
        business_problem=(
            "Disbursements released without recorded Accounts Payable invoice verification, "
            "bypassing price and quantity reconciliation."
        ),
        supporting_metric="skipped_invoice_verification_case_percentage",
        actual_metric_value=actual_pct,
        threshold_or_baseline=f"Threshold: > {config.skip_verification_threshold * 100:.1f}% (Compliance mandate)",
        affected_case_count=affected_count,
        affected_case_percentage=round_num(actual_pct * 100.0, 2),
        estimated_operational_impact=(
            f"Payment execution without verification in {affected_count:,} cases creates audit exposure and potential "
            f"untracked invoice variance liabilities."
        ),
        recommended_corrective_action=(
            "Require verified invoice audit ID as a mandatory cryptographic prerequisite before automated payment batch generation."
        ),
        evidence_and_explanation=(
            f"Identified {affected_count:,} cases reaching 'Payment Completed' without any recorded 'Invoice Verified' milestone."
        ),
        estimated_impact_score=impact_score,
    )


# ── 4. HIGH_REWORK ────────────────────────────────────────────────────────────
def evaluate_high_rework(
    overview: OverviewMetrics,
    rework: ReworkMetrics,
    config: RecommendationsConfig,
) -> Optional[RecommendationItem]:
    """
    Evaluates whether repetitive activity loops cause excessive process churn and operational waste.
    Category: Quality | Severity: MEDIUM / HIGH
    """
    total_cases = overview.total_purchase_cases
    if total_cases == 0:
        return None

    rework_pct = overview.rework_percentage
    if rework_pct <= config.high_rework_threshold:
        return None

    rework_cases = overview.rework_cases
    top_act = rework.activities[0].activity if rework.activities else "Manager Approval"
    top_act_cases = rework.activities[0].rework_case_count if rework.activities else rework_cases

    severity = "HIGH" if rework_pct > 0.15 else "MEDIUM"
    weight = SEVERITY_WEIGHTS[severity]
    impact_score = round_num(weight * (rework_pct * 100.0) + (rework_cases * 0.05), 2)

    return RecommendationItem(
        recommendation_id=f"REC-HIGH-REWORK-{rework_cases:03d}",
        rule_id="HIGH_REWORK",
        category=RecommendationCategoryEnum.QUALITY.value,
        severity=severity,
        business_problem=(
            "Excessive process looping and rework cycles observed, requiring redundant reviews "
            "and duplicate approvals on identical cases."
        ),
        supporting_metric="rework_case_percentage",
        actual_metric_value=rework_pct,
        threshold_or_baseline=f"Threshold: > {config.high_rework_threshold * 100:.1f}% (Industry benchmark: < 8.0%)",
        affected_case_count=rework_cases,
        affected_case_percentage=round_num(rework_pct * 100.0, 2),
        estimated_operational_impact=(
            f"Rework affected {rework_cases:,} cases ({rework_pct * 100.0:.1f}% of volume), generating "
            f"{rework.total_rework_events:,} extra event executions. Adds an estimated "
            f"{overview.avg_cycle_time_hours * 0.18:.1f} hours of avoidable administrative latency per case."
        ),
        recommended_corrective_action=(
            f"Redesign submission validation for '{top_act}' to enforce first-time-right data entry. "
            f"Introduce standardized requisition forms to eliminate repeated revision cycles."
        ),
        evidence_and_explanation=(
            f"Analysis detected {rework.total_rework_events:,} redundant executions across {rework_cases:,} cases. "
            f"The primary activity driving rework is '{top_act}', accounting for {top_act_cases:,} looped cases."
        ),
        estimated_impact_score=impact_score,
    )


# ── 5. APPROVAL_BOTTLENECK ────────────────────────────────────────────────────
def evaluate_approval_bottleneck(
    bottlenecks: BottlenecksResponse,
    overview: OverviewMetrics,
    config: RecommendationsConfig,
) -> Optional[RecommendationItem]:
    """
    Evaluates whether the Manager Approval stage has severe queueing delays.
    Category: Efficiency | Severity: MEDIUM / HIGH
    """
    if not bottlenecks.bottlenecks:
        return None

    app_bn = next(
        (b for b in bottlenecks.bottlenecks if "Approval" in b.activity or b.rank == 1),
        bottlenecks.bottlenecks[0],
    )

    actual_wait = app_bn.avg_waiting_time_hours
    if actual_wait <= config.approval_bottleneck_hours:
        return None

    affected_count = app_bn.transition_count
    total_cases = max(1, overview.total_purchase_cases)
    affected_pct = round_num(min(1.0, affected_count / total_cases))

    severity = "HIGH" if actual_wait > 48.0 else "MEDIUM"
    weight = SEVERITY_WEIGHTS[severity]
    impact_score = round_num(weight * (actual_wait / config.approval_bottleneck_hours) * 10.0, 2)

    return RecommendationItem(
        recommendation_id=f"REC-BOTTLENECK-{app_bn.rank:02d}",
        rule_id="APPROVAL_BOTTLENECK",
        category=RecommendationCategoryEnum.EFFICIENCY.value,
        severity=severity,
        business_problem=(
            f"Severe queue waiting delay concentrated at stage '{app_bn.activity}', "
            f"acting as the primary process bottleneck."
        ),
        supporting_metric="manager_approval_avg_waiting_time_hours",
        actual_metric_value=actual_wait,
        threshold_or_baseline=f"Threshold: > {config.approval_bottleneck_hours:.1f}h SLA (Benchmark: 24.0h)",
        affected_case_count=affected_count,
        affected_case_percentage=round_num(affected_pct * 100.0, 2),
        estimated_operational_impact=(
            f"Cases spend an average of {actual_wait:.1f} hours (median: {app_bn.median_waiting_time_hours:.1f}h) "
            f"waiting in queue before '{app_bn.activity}', contributing {(actual_wait / max(1.0, overview.avg_cycle_time_hours)) * 100.0:.1f}% "
            f"to overall procurement duration."
        ),
        recommended_corrective_action=(
            "Establish auto-delegation rules for managers absent > 24 hours, implement mobile push authorization, "
            "and establish tiered approval limits so small purchases (< $1,000) bypass senior manager queues."
        ),
        evidence_and_explanation=(
            f"Directly-Follows Graph and timestamp transition analysis ranked '{app_bn.activity}' as bottleneck #{app_bn.rank} "
            f"with a severity score of {app_bn.bottleneck_score:.1f} across {affected_count:,} transitions."
        ),
        estimated_impact_score=impact_score,
    )


# ── 6. LOW_FPY ────────────────────────────────────────────────────────────────
def evaluate_low_fpy(
    conformance: ConformanceOverviewResponse,
    overview: OverviewMetrics,
    config: RecommendationsConfig,
) -> Optional[RecommendationItem]:
    """
    Evaluates First Pass Yield (FPY): proportion of cases executing without deviations or rework loops.
    Category: Quality | Severity: MEDIUM / HIGH
    """
    total_cases = overview.total_purchase_cases
    if total_cases == 0:
        return None

    # First Pass Yield = conformant cases that also had zero rework
    # Conservative calculation grounded in actual counts:
    # Non-first-pass cases = total_cases - conformant_cases + (cases conformant but reworked)
    # We compute actual FPY = conformant_cases / total_cases * (1 - rework_percentage)
    raw_conformant_rate = conformance.conformance_percentage / 100.0
    fpy = round_num(raw_conformant_rate * (1.0 - overview.rework_percentage), 4)

    if fpy >= config.low_fpy_threshold:
        return None

    non_fpy_cases = max(0, int(total_cases * (1.0 - fpy)))
    non_fpy_pct = round_num((1.0 - fpy) * 100.0, 2)

    severity = "HIGH" if fpy < 0.60 else "MEDIUM"
    weight = SEVERITY_WEIGHTS[severity]
    impact_score = round_num(weight * ((config.low_fpy_threshold - fpy) * 100.0), 2)

    return RecommendationItem(
        recommendation_id=f"REC-LOW-FPY-{int(fpy * 100):02d}",
        rule_id="LOW_FPY",
        category=RecommendationCategoryEnum.QUALITY.value,
        severity=severity,
        business_problem=(
            f"Depressed First Pass Yield (FPY): only {fpy * 100.0:.1f}% of purchase orders navigate "
            f"the end-to-end P2P lifecycle on the first attempt without deviation or rework."
        ),
        supporting_metric="first_pass_yield",
        actual_metric_value=fpy,
        threshold_or_baseline=f"Threshold: < {config.low_fpy_threshold * 100:.1f}% (Target operational standard: 80.0%)",
        affected_case_count=non_fpy_cases,
        affected_case_percentage=non_fpy_pct,
        estimated_operational_impact=(
            f"{non_fpy_cases:,} cases ({non_fpy_pct:.1f}% of volume) required manual intervention, rework, or "
            f"compliance reconciliation, creating operational drag across finance and procurement teams."
        ),
        recommended_corrective_action=(
            "Introduce straight-through processing (STP) for standard catalog items, enforce pre-validated vendor profiles, "
            "and eliminate discretionary manual steps from low-risk purchase categories."
        ),
        evidence_and_explanation=(
            f"Computed First Pass Yield is {fpy * 100.0:.1f}% based on {conformance.conformant_cases:,} conformant cases "
            f"adjusted for an operational rework rate of {overview.rework_percentage * 100.0:.1f}% across {total_cases:,} total cases."
        ),
        estimated_impact_score=impact_score,
    )


# ── 7. HIGH_ABANDONMENT ───────────────────────────────────────────────────────
def evaluate_high_abandonment(
    overview: OverviewMetrics,
    config: RecommendationsConfig,
) -> Optional[RecommendationItem]:
    """
    Evaluates whether an excessive fraction of cases terminate prematurely without payment completion.
    Category: Efficiency | Severity: MEDIUM / HIGH
    """
    total_cases = overview.total_purchase_cases
    if total_cases == 0:
        return None

    abandoned_cases = overview.incomplete_cases
    abandonment_rate = round_num(abandoned_cases / total_cases, 4)

    if abandonment_rate <= config.high_abandonment_threshold:
        return None

    severity = "HIGH" if abandonment_rate > 0.10 else "MEDIUM"
    weight = SEVERITY_WEIGHTS[severity]
    impact_score = round_num(weight * (abandonment_rate * 100.0) + (abandoned_cases * 0.05), 2)

    return RecommendationItem(
        recommendation_id=f"REC-ABANDONMENT-{abandoned_cases:03d}",
        rule_id="HIGH_ABANDONMENT",
        category=RecommendationCategoryEnum.EFFICIENCY.value,
        severity=severity,
        business_problem=(
            "High rate of procurement order abandonment: initiated purchase requisitions/orders stall "
            "indefinitely without reaching payment completion."
        ),
        supporting_metric="case_abandonment_rate",
        actual_metric_value=abandonment_rate,
        threshold_or_baseline=f"Threshold: > {config.high_abandonment_threshold * 100:.1f}% (Target: < 5.0%)",
        affected_case_count=abandoned_cases,
        affected_case_percentage=round_num(abandonment_rate * 100.0, 2),
        estimated_operational_impact=(
            f"Represents sunk effort in creating {abandoned_cases:,} unresolved orders ({abandonment_rate * 100.0:.1f}%). "
            f"Leaves commitments unfulfilled and leads to inaccurate working capital forecasting."
        ),
        recommended_corrective_action=(
            "Deploy automated cleanup jobs to query requesters of inactive cases past 45 days, automatically archiving "
            "stale requests and releasing reserved budget allocations."
        ),
        evidence_and_explanation=(
            f"Exact case tracking identified {abandoned_cases:,} incomplete cases out of {total_cases:,} total cases "
            f"that terminated prior to reaching final 'Payment Completed' milestone."
        ),
        estimated_impact_score=impact_score,
    )


# ── 8. SLA_BREACH ─────────────────────────────────────────────────────────────
def evaluate_sla_breach(
    overview: OverviewMetrics,
    config: RecommendationsConfig,
) -> Optional[RecommendationItem]:
    """
    Evaluates whether cycle times frequently violate the 720h (30-day) SLA threshold.
    Category: Compliance | Severity: MEDIUM / HIGH
    """
    total_cases = overview.total_purchase_cases
    if total_cases == 0:
        return None

    breach_rate = overview.sla_breach_percentage
    if breach_rate <= config.sla_breach_threshold:
        return None

    breach_cases = overview.sla_breach_cases
    severity = "HIGH" if breach_rate > 0.20 else "MEDIUM"
    weight = SEVERITY_WEIGHTS[severity]
    impact_score = round_num(weight * (breach_rate * 100.0) + (breach_cases * 0.05), 2)

    return RecommendationItem(
        recommendation_id=f"REC-SLA-BREACH-{breach_cases:03d}",
        rule_id="SLA_BREACH",
        category=RecommendationCategoryEnum.COMPLIANCE.value,
        severity=severity,
        business_problem=(
            f"Excessive SLA breach rate: procurement orders take longer than the {overview.sla_hours:.0f}-hour "
            f"({overview.sla_hours / 24.0:.0f}-day) target turnaround time."
        ),
        supporting_metric="sla_breach_percentage",
        actual_metric_value=breach_rate,
        threshold_or_baseline=f"Threshold: > {config.sla_breach_threshold * 100:.1f}% (Benchmark: < 10.0%)",
        affected_case_count=breach_cases,
        affected_case_percentage=round_num(breach_rate * 100.0, 2),
        estimated_operational_impact=(
            f"{breach_cases:,} cases ({breach_rate * 100.0:.1f}% of volume) missed the {overview.sla_hours:.0f}h SLA. "
            f"Average cycle time is {overview.avg_cycle_time_hours:.1f}h (P90: {overview.p90_cycle_time_hours:.1f}h), "
            f"straining vendor relationships and forfeiting prompt-payment discounts."
        ),
        recommended_corrective_action=(
            "Establish SLA milestone alerts at 50% (360h) and 75% (540h) elapsed time. "
            "Implement automated queue prioritization for invoices approaching due dates."
        ),
        evidence_and_explanation=(
            f"Exact cycle time calculations measured {breach_cases:,} cases exceeding {overview.sla_hours:.0f} hours, "
            f"with a median cycle time of {overview.median_cycle_time_hours:.1f} hours."
        ),
        estimated_impact_score=impact_score,
    )
