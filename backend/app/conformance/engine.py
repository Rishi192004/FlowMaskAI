"""
Conformance Checking & Deviation Detection Engine.
Performs token-based replay and configurable business rule evaluations against
business event logs. Detects skipped steps, early invoice verification, repeated approvals,
out-of-order execution, and unexpected activities with exact culprit event tracing.
"""
from __future__ import annotations

import math
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session

from app.conformance.rules import get_conformance_rules
from app.models.dataset import CleanedEvent
from app.process_mining.converter import fetch_cleaned_event_records
from app.schemas.conformance import (
    CaseDeviationDetail,
    CaseDeviationItem,
    CaseDeviationsListResponse,
    ConformanceOverviewResponse,
    ConformanceRulesConfig,
    DeviationSummaryItem,
)


def evaluate_case_conformance(
    case_id: str,
    trace: List[Dict[str, Any]],
    rules: ConformanceRulesConfig,
) -> CaseDeviationItem:
    """
    Evaluates a single case trace against the reference model and configurable business rules.
    Pinpoints what went wrong, why, and which exact event caused the deviation.
    """
    trace.sort(key=lambda x: x["time:timestamp"])
    total_events = len(trace)

    start_ts = trace[0]["time:timestamp"]
    end_ts = trace[-1]["time:timestamp"]
    duration_hours = round(max(0.0, (end_ts - start_ts).total_seconds() / 3600.0), 2)

    activities = [e["concept:name"] for e in trace]
    deviations: List[CaseDeviationDetail] = []

    ref_seq = rules.reference_sequence
    ref_set = set(ref_seq)
    ref_index_map = {act: i for i, act in enumerate(ref_seq)}

    # 1. Rule Check: Unexpected Activities
    if rules.prohibit_unexpected_activities:
        for ev in trace:
            act = ev["concept:name"]
            if act not in ref_set:
                deviations.append(CaseDeviationDetail(
                    deviation_type="UNEXPECTED_ACTIVITY",
                    severity="MEDIUM",
                    description=f"Activity '{act}' is not part of the standard reference model.",
                    culprit_activity=act,
                    culprit_event_id=ev.get("id"),
                    culprit_timestamp=ev.get("time:timestamp"),
                    expected=f"One of standard activities: {', '.join(ref_seq[:4])}...",
                    actual=f"Observed '{act}'",
                ))

    # 2. Rule Check: Skipped Manager Approval
    if rules.require_manager_approval:
        po_created_events = [ev for ev in trace if ev["concept:name"] == "Purchase Order Created"]
        approval_events = [ev for ev in trace if ev["concept:name"] == "Manager Approval"]

        for po_ev in po_created_events:
            po_time = po_ev["time:timestamp"]
            prior_approvals = [ap for ap in approval_events if ap["time:timestamp"] <= po_time]
            if not prior_approvals:
                deviations.append(CaseDeviationDetail(
                    deviation_type="SKIPPED_APPROVAL",
                    severity="HIGH",
                    description="Purchase Order was created without authorized Manager Approval (unauthorized procurement).",
                    culprit_activity="Purchase Order Created",
                    culprit_event_id=po_ev.get("id"),
                    culprit_timestamp=po_time,
                    expected="Manager Approval preceding Purchase Order Created",
                    actual="Purchase Order Created occurred without prior approval",
                ))

    # 3. Rule Check: Early Invoice Verification (Invoice Verified before Goods Received)
    if rules.prohibit_early_invoice_verification:
        inv_verified_events = [ev for ev in trace if ev["concept:name"] == "Invoice Verified"]
        goods_received_events = [ev for ev in trace if ev["concept:name"] == "Goods Received"]

        for iv_ev in inv_verified_events:
            iv_time = iv_ev["time:timestamp"]
            prior_gr = [gr for gr in goods_received_events if gr["time:timestamp"] <= iv_time]
            if not prior_gr:
                deviations.append(CaseDeviationDetail(
                    deviation_type="EARLY_INVOICE_VERIFICATION",
                    severity="HIGH",
                    description="Invoice was verified before goods were physically received (3-way match control bypass).",
                    culprit_activity="Invoice Verified",
                    culprit_event_id=iv_ev.get("id"),
                    culprit_timestamp=iv_time,
                    expected="Goods Received prior to Invoice Verified",
                    actual="Invoice Verified executed before any Goods Received event",
                ))

    # 4. Rule Check: Skipped Invoice Verification (Payment without Invoice Verified)
    if getattr(rules, "require_invoice_verification", True):
        payment_events = [ev for ev in trace if ev["concept:name"] in ("Payment Completed", "Payment Executed", "Invoice Paid")]
        inv_verified_events = [ev for ev in trace if ev["concept:name"] == "Invoice Verified"]
        for p_ev in payment_events:
            p_time = p_ev["time:timestamp"]
            prior_iv = [iv for iv in inv_verified_events if iv["time:timestamp"] <= p_time]
            if not prior_iv:
                deviations.append(CaseDeviationDetail(
                    deviation_type="SKIPPED_INVOICE_VERIFICATION",
                    severity="HIGH",
                    description="Payment was completed without prior Invoice Verification (disbursement control bypass).",
                    culprit_activity=p_ev["concept:name"],
                    culprit_event_id=p_ev.get("id"),
                    culprit_timestamp=p_time,
                    expected="Invoice Verified preceding Payment Completed",
                    actual=f"{p_ev['concept:name']} occurred without prior invoice verification",
                ))

    # 5. Rule Check: Repeated Approval (Rework on Approval)
    if not rules.allow_repeated_approval:
        approval_events = [ev for ev in trace if ev["concept:name"] == "Manager Approval"]
        if len(approval_events) > 1:
            for rep_ev in approval_events[1:]:
                deviations.append(CaseDeviationDetail(
                    deviation_type="REPEATED_APPROVAL",
                    severity="MEDIUM",
                    description=f"Manager Approval was repeated {len(approval_events)} times (redundant authorization cycle).",
                    culprit_activity="Manager Approval",
                    culprit_event_id=rep_ev.get("id"),
                    culprit_timestamp=rep_ev.get("time:timestamp"),
                    expected="Single Manager Approval authorization",
                    actual=f"Repeated execution {len(approval_events)} times",
                ))

    # 5. Rule Check: Incomplete Process (Missing Payment Completed)
    if rules.require_payment_completion:
        has_payment = any(
            ev["concept:name"] in ("Payment Completed", "Payment Executed", "Invoice Paid")
            for ev in trace
        )
        if not has_payment:
            last_ev = trace[-1]
            deviations.append(CaseDeviationDetail(
                deviation_type="INCOMPLETE_PROCESS",
                severity="MEDIUM",
                description="Case terminated prematurely without reaching Payment Completed.",
                culprit_activity=last_ev["concept:name"],
                culprit_event_id=last_ev.get("id"),
                culprit_timestamp=last_ev.get("time:timestamp"),
                expected="Payment Completed as final milestone",
                actual=f"Process terminated at '{last_ev['concept:name']}'",
            ))

    # 6. Rule Check: Out of Expected Sequence
    if rules.strict_sequence:
        seen_indices = []
        for ev in trace:
            act = ev["concept:name"]
            if act in ref_index_map:
                curr_idx = ref_index_map[act]
                if seen_indices and curr_idx < max(seen_indices):
                    # Inverted order
                    prev_max_act = ref_seq[max(seen_indices)]
                    deviations.append(CaseDeviationDetail(
                        deviation_type="OUT_OF_ORDER",
                        severity="MEDIUM",
                        description=f"Activity '{act}' executed out of order after '{prev_max_act}'.",
                        culprit_activity=act,
                        culprit_event_id=ev.get("id"),
                        culprit_timestamp=ev.get("time:timestamp"),
                        expected=f"Chronological flow according to reference model",
                        actual=f"'{act}' observed after '{prev_max_act}'",
                    ))
                seen_indices.append(curr_idx)

    is_conformant = len(deviations) == 0

    # Calculate token-based replay fitness approximation
    # Fitness = max(0.0, 1.0 - (penalties / (2 * total_events)))
    penalty = sum(1.5 if d.severity == "HIGH" else 1.0 for d in deviations)
    denom = max(1.0, 2.0 * float(total_events))
    fitness_score = round(max(0.0, min(1.0, 1.0 - (penalty / denom))), 4)

    return CaseDeviationItem(
        case_id=case_id,
        is_conformant=is_conformant,
        fitness_score=fitness_score,
        total_events=total_events,
        duration_hours=duration_hours,
        deviations=deviations,
    )


def run_conformance_check(
    db: Session,
    dataset_id: uuid.UUID,
    rules: Optional[ConformanceRulesConfig] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    department: Optional[str] = None,
    vendor_id: Optional[str] = None,
) -> Tuple[List[CaseDeviationItem], ConformanceRulesConfig]:
    """
    Executes full conformance checking across all cases in the dataset.
    """
    active_rules = rules or get_conformance_rules(dataset_id)
    records = fetch_cleaned_event_records(
        db=db,
        dataset_id=dataset_id,
        start_date=start_date,
        end_date=end_date,
        department=department,
        vendor_id=vendor_id,
    )

    cases_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        cases_map[r["case:concept:name"]].append(r)

    results: List[CaseDeviationItem] = []
    for cid, trace in cases_map.items():
        res = evaluate_case_conformance(cid, trace, active_rules)
        results.append(res)

    results.sort(key=lambda x: (x.is_conformant, x.fitness_score, x.case_id))
    return results, active_rules


def get_conformance_overview_response(
    db: Session,
    dataset_id: uuid.UUID,
    rules: Optional[ConformanceRulesConfig] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> ConformanceOverviewResponse:
    """Calculates overall conformance percentage and deviation frequency breakdown."""
    case_results, active_rules = run_conformance_check(
        db=db,
        dataset_id=dataset_id,
        rules=rules,
        start_date=start_date,
        end_date=end_date,
    )

    total_c = len(case_results)
    if total_c == 0:
        return ConformanceOverviewResponse(
            dataset_id=dataset_id,
            total_cases=0,
            conformant_cases=0,
            deviant_cases=0,
            conformance_percentage=0.0,
            average_fitness_score=0.0,
            deviation_breakdown=[],
            active_rules=active_rules,
        )

    conformant_c = sum(1 for c in case_results if c.is_conformant)
    deviant_c = total_c - conformant_c
    conf_pct = round((conformant_c / total_c) * 100.0, 2)
    avg_fitness = round(sum(c.fitness_score for c in case_results) / total_c, 4)

    # Breakdown by deviation type
    dev_type_cases: Dict[str, set] = defaultdict(set)
    dev_type_meta = {
        "SKIPPED_APPROVAL": ("Compliance", "HIGH", "Purchase Order created without prior authorized Manager Approval."),
        "EARLY_INVOICE_VERIFICATION": ("Risk", "HIGH", "Invoice verified before goods receipt (3-way match failure)."),
        "SKIPPED_INVOICE_VERIFICATION": ("Compliance", "HIGH", "Payment completed without prior invoice verification (disbursement control failure)."),
        "REPEATED_APPROVAL": ("Efficiency", "MEDIUM", "Manager Approval repeated multiple times causing process looping."),
        "INCOMPLETE_PROCESS": ("Quality", "MEDIUM", "Case terminated prematurely without recorded payment completion."),
        "OUT_OF_ORDER": ("Quality", "MEDIUM", "Activities executed out of standard chronological sequence."),
        "UNEXPECTED_ACTIVITY": ("Compliance", "MEDIUM", "Non-standard activities executed outside the reference workflow."),
    }

    for c in case_results:
        for d in c.deviations:
            dev_type_cases[d.deviation_type].add(c.case_id)

    breakdown: List[DeviationSummaryItem] = []
    for dtype, cids in dev_type_cases.items():
        count = len(cids)
        pct = round((count / total_c) * 100.0, 2)
        cat, sev, desc = dev_type_meta.get(dtype, ("General", "MEDIUM", "Process deviation."))
        breakdown.append(DeviationSummaryItem(
            deviation_type=dtype,
            category=cat,
            severity=sev,
            affected_cases=count,
            percentage_of_cases=pct,
            description=desc,
        ))

    breakdown.sort(key=lambda x: x.affected_cases, reverse=True)

    return ConformanceOverviewResponse(
        dataset_id=dataset_id,
        total_cases=total_c,
        conformant_cases=conformant_c,
        deviant_cases=deviant_c,
        conformance_percentage=conf_pct,
        average_fitness_score=avg_fitness,
        deviation_breakdown=breakdown,
        active_rules=active_rules,
    )


def get_case_deviations_response(
    db: Session,
    dataset_id: uuid.UUID,
    rules: Optional[ConformanceRulesConfig] = None,
    filter_deviant_only: bool = False,
    page: int = 1,
    page_size: int = 20,
) -> CaseDeviationsListResponse:
    """Returns paginated case-level deviation reports with exact culprit events."""
    case_results, _ = run_conformance_check(db=db, dataset_id=dataset_id, rules=rules)

    if filter_deviant_only:
        filtered = [c for c in case_results if not c.is_conformant]
    else:
        filtered = case_results

    total_c = len(case_results)
    conf_c = sum(1 for c in case_results if c.is_conformant)
    dev_c = total_c - conf_c

    total_filtered = len(filtered)
    pages = math.ceil(total_filtered / page_size) if total_filtered > 0 else 0
    items = filtered[(page - 1) * page_size : page * page_size]

    return CaseDeviationsListResponse(
        dataset_id=dataset_id,
        total_cases=total_c,
        conformant_cases_count=conf_c,
        deviant_cases_count=dev_c,
        page=page,
        page_size=page_size,
        pages=pages,
        cases=items,
    )
