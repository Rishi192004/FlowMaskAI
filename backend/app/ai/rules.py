"""
Independent, Configurable Rule Evaluators for Grounded Process Mining Recommendations.
Every rule operates strictly on computed analytical metrics and database records.
Zero fabrication: parameterized templates populate from real case counts and calculated values.
"""
from __future__ import annotations

from typing import Optional

from app.schemas.ai import (
    RecommendationCategoryEnum,
    RecommendationItem,
    RecommendationsConfig,
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
            "Purchase orders were recorded without a preceding manager-approval event in the case history."
        ),
        supporting_metric="skipped_approval_case_percentage",
        actual_metric_value=actual_pct,
        threshold_or_baseline=f"Configured threshold: > {config.skip_approval_threshold * 100:.1f}%",
        affected_case_count=affected_count,
        affected_case_percentage=round_num(actual_pct * 100.0, 2),
        estimated_operational_impact=(
            f"{affected_count:,} of {total_cases:,} cases ({actual_pct * 100.0:.1f}%) "
            f"have no recorded approval before purchase-order creation."
        ),
        recommended_corrective_action=(
            "Implement automated ERP approval gating that prohibits PO release until digital manager sign-off is logged. "
            f"Audit all {affected_count:,} unapproved orders for retroactive ratification or supplier contract cancellations."
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
            "Invoice verification was recorded before goods receipt in affected cases."
        ),
        supporting_metric="early_invoice_verification_case_percentage",
        actual_metric_value=actual_pct,
        threshold_or_baseline=f"Configured threshold: > {config.early_invoice_threshold * 100:.1f}%",
        affected_case_count=affected_count,
        affected_case_percentage=round_num(actual_pct * 100.0, 2),
        estimated_operational_impact=(
            f"The three-way-match sequence was not observed in {affected_count:,} cases "
            f"({actual_pct * 100.0:.1f}% of analyzed cases)."
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
            "Payments were recorded without a preceding invoice-verification event."
        ),
        supporting_metric="skipped_invoice_verification_case_percentage",
        actual_metric_value=actual_pct,
        threshold_or_baseline=f"Configured threshold: > {config.skip_verification_threshold * 100:.1f}%",
        affected_case_count=affected_count,
        affected_case_percentage=round_num(actual_pct * 100.0, 2),
        estimated_operational_impact=(
            f"{affected_count:,} payment cases ({actual_pct * 100.0:.1f}% of analyzed cases) "
            f"have no preceding invoice-verification record."
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
    top_activity = rework.activities[0] if rework.activities else None
    top_act = top_activity.activity if top_activity else None
    top_act_cases = top_activity.rework_case_count if top_activity else None

    severity = "HIGH" if rework_pct > 0.15 else "MEDIUM"
    weight = SEVERITY_WEIGHTS[severity]
    impact_score = round_num(weight * (rework_pct * 100.0) + (rework_cases * 0.05), 2)

    return RecommendationItem(
        recommendation_id=f"REC-HIGH-REWORK-{rework_cases:03d}",
        rule_id="HIGH_REWORK",
        category=RecommendationCategoryEnum.QUALITY.value,
        severity=severity,
        business_problem=(
            "Repeated activity executions exceed the configured rework-rate threshold."
        ),
        supporting_metric="rework_case_percentage",
        actual_metric_value=rework_pct,
        threshold_or_baseline=f"Configured threshold: > {config.high_rework_threshold * 100:.1f}%",
        affected_case_count=rework_cases,
        affected_case_percentage=round_num(rework_pct * 100.0, 2),
        estimated_operational_impact=(
            f"Rework affected {rework_cases:,} cases ({rework_pct * 100.0:.1f}% of volume), generating "
            f"{rework.total_rework_events:,} repeated event executions."
        ),
        recommended_corrective_action=(
            (
                f"Review validation and handoffs for '{top_act}' and identify why it repeats."
                if top_act
                else "Review repeated activity patterns and identify the causes of rework."
            )
        ),
        evidence_and_explanation=(
            (
                f"Analysis detected {rework.total_rework_events:,} repeated event executions across "
                f"{rework_cases:,} cases. The most frequent repeated activity was '{top_act}', "
                f"present in {top_act_cases:,} cases."
                if top_act
                else f"Analysis detected {rework.total_rework_events:,} repeated event executions "
                f"across {rework_cases:,} cases."
            )
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
        (b for b in bottlenecks.bottlenecks if b.activity.casefold() == "manager approval"),
        None,
    )
    if app_bn is None:
        return None

    actual_wait = app_bn.avg_waiting_time_hours
    if actual_wait <= config.approval_bottleneck_hours or app_bn.affected_case_count == 0:
        return None

    affected_count = app_bn.affected_case_count
    total_cases = overview.total_purchase_cases
    if total_cases == 0:
        return None
    affected_pct = round_num(affected_count / total_cases)

    severity = "HIGH" if actual_wait > 48.0 else "MEDIUM"
    weight = SEVERITY_WEIGHTS[severity]
    impact_score = round_num(weight * (actual_wait / config.approval_bottleneck_hours) * 10.0, 2)

    return RecommendationItem(
        recommendation_id=f"REC-BOTTLENECK-{app_bn.rank:02d}",
        rule_id="APPROVAL_BOTTLENECK",
        category=RecommendationCategoryEnum.EFFICIENCY.value,
        severity=severity,
        business_problem=(
            f"Approval-stage queue waiting exceeds the configured threshold at '{app_bn.activity}'."
        ),
        supporting_metric="manager_approval_avg_waiting_time_hours",
        actual_metric_value=actual_wait,
        threshold_or_baseline=f"Configured threshold: > {config.approval_bottleneck_hours:.1f} hours",
        affected_case_count=affected_count,
        affected_case_percentage=round_num(affected_pct * 100.0, 2),
        estimated_operational_impact=(
            f"Cases spend an average of {actual_wait:.1f} hours (median: {app_bn.median_waiting_time_hours:.1f}h) "
            f"waiting before '{app_bn.activity}' across {affected_count:,} affected cases."
        ),
        recommended_corrective_action=(
            "Review the approval queue, clarify ownership and escalation paths, and consider routing rules "
            "for approvals that remain pending."
        ),
        evidence_and_explanation=(
            f"Timestamp transition analysis measured a {actual_wait:.1f}-hour average wait at "
            f"'{app_bn.activity}' across {app_bn.transition_count:,} transitions and "
            f"{affected_count:,} distinct cases."
        ),
        estimated_impact_score=impact_score,
    )


# ── 6. LOW_FPY ────────────────────────────────────────────────────────────────
def evaluate_low_fpy(
    overview: OverviewMetrics,
    first_pass_case_count: int,
    config: RecommendationsConfig,
) -> Optional[RecommendationItem]:
    """
    Evaluates First Pass Yield (FPY): proportion of cases executing without deviations or rework loops.
    Category: Quality | Severity: MEDIUM / HIGH
    """
    total_cases = overview.total_purchase_cases
    if total_cases == 0:
        return None
    if not 0 <= first_pass_case_count <= total_cases:
        raise ValueError("first_pass_case_count must be between zero and total_purchase_cases")

    fpy = round_num(first_pass_case_count / total_cases, 4)

    if fpy >= config.low_fpy_threshold:
        return None

    non_fpy_cases = total_cases - first_pass_case_count
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
            f"First Pass Yield is {fpy * 100.0:.1f}%: the share of cases conformant on the first pass "
            f"and without repeated activity is below the configured target."
        ),
        supporting_metric="first_pass_yield",
        actual_metric_value=fpy,
        threshold_or_baseline=f"Configured threshold: < {config.low_fpy_threshold * 100:.1f}%",
        affected_case_count=non_fpy_cases,
        affected_case_percentage=non_fpy_pct,
        estimated_operational_impact=(
            f"{first_pass_case_count:,} of {total_cases:,} cases were first-pass conformant; "
            f"{non_fpy_cases:,} cases ({non_fpy_pct:.1f}%) had at least one deviation or repeated activity."
        ),
        recommended_corrective_action=(
            "Introduce straight-through processing (STP) for standard catalog items, enforce pre-validated vendor profiles, "
            "and eliminate discretionary manual steps from low-risk purchase categories."
        ),
        evidence_and_explanation=(
            f"Computed First Pass Yield is {fpy * 100.0:.1f}%: {first_pass_case_count:,} cases were conformant "
            f"and had no repeated activities, out of {total_cases:,} cases."
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

    incomplete_cases = overview.incomplete_cases
    incomplete_rate = round_num(incomplete_cases / total_cases, 4)

    if incomplete_rate <= config.high_abandonment_threshold:
        return None

    severity = "HIGH" if incomplete_rate > 0.10 else "MEDIUM"
    weight = SEVERITY_WEIGHTS[severity]
    impact_score = round_num(weight * (incomplete_rate * 100.0) + (incomplete_cases * 0.05), 2)

    return RecommendationItem(
        recommendation_id=f"REC-ABANDONMENT-{incomplete_cases:03d}",
        rule_id="HIGH_ABANDONMENT",
        category=RecommendationCategoryEnum.EFFICIENCY.value,
        severity=severity,
        business_problem=(
            "A high share of observed cases has no payment-completion event in the available event log."
        ),
        supporting_metric="incomplete_case_rate",
        actual_metric_value=incomplete_rate,
        threshold_or_baseline=f"Configured threshold: > {config.high_abandonment_threshold * 100:.1f}%",
        affected_case_count=incomplete_cases,
        affected_case_percentage=round_num(incomplete_rate * 100.0, 2),
        estimated_operational_impact=(
            f"{incomplete_cases:,} of {total_cases:,} observed cases ({incomplete_rate * 100.0:.1f}%) "
            f"have no recorded payment-completion event."
        ),
        recommended_corrective_action=(
            "Review incomplete cases with process owners and distinguish genuinely stalled work from cases "
            "whose completion events were not captured in the source log."
        ),
        evidence_and_explanation=(
            f"The event log contains {incomplete_cases:,} cases without a recorded completion activity "
            f"out of {total_cases:,} total cases. The event log alone cannot establish whether these cases "
            f"were abandoned or are still in progress."
        ),
        estimated_impact_score=impact_score,
    )


# ── 8. SLA_BREACH ─────────────────────────────────────────────────────────────
def evaluate_sla_breach(
    overview: OverviewMetrics,
    config: RecommendationsConfig,
) -> Optional[RecommendationItem]:
    """
    Evaluates whether cycle times frequently violate the configured SLA threshold.
    Category: Compliance | Severity: MEDIUM / HIGH
    """
    total_cases = overview.total_purchase_cases
    if total_cases == 0:
        return None

    eligible_cases = overview.completed_cases or total_cases
    breach_rate = overview.sla_breach_percentage
    if breach_rate <= config.sla_breach_threshold:
        return None

    breach_cases = overview.sla_breach_cases
    affected_case_percentage = round_num(breach_cases / total_cases * 100.0, 2)
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
        threshold_or_baseline=(
            f"Configured threshold: > {config.sla_breach_threshold * 100:.1f}% "
            "of cases with cycle-time measurements"
        ),
        affected_case_count=breach_cases,
        affected_case_percentage=affected_case_percentage,
        estimated_operational_impact=(
            f"{breach_cases:,} of {eligible_cases:,} cycle-time cases ({breach_rate * 100.0:.1f}%) "
            f"exceeded the {overview.sla_hours:.0f}-hour cycle-time target."
        ),
        recommended_corrective_action=(
            "Review the breached cases and identify the process stages with the largest measured delays; "
            "consider stage-level alerts and queue prioritization for cases approaching the configured SLA."
        ),
        evidence_and_explanation=(
            f"Exact cycle time calculations measured {breach_cases:,} cases exceeding {overview.sla_hours:.0f} hours, "
            f"out of {eligible_cases:,} cases used for cycle-time analysis; median cycle time was "
            f"{overview.median_cycle_time_hours:.1f} hours."
        ),
        estimated_impact_score=impact_score,
    )
