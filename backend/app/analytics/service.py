"""
Operational Analytics Engine Service.
Executes business metric calculations backed by SQL aggregations.
Supports dataset filtering, date ranges, SLA thresholds, and explainable bottleneck rankings.
"""
from __future__ import annotations

import math
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.analytics.queries import (
    COMPLETION_ACTIVITIES,
    fetch_activity_transitions_sql,
    fetch_case_attributes_and_events,
    fetch_case_durations_sql,
    fetch_rework_sql,
)
from app.core.exceptions import NotFoundError
from app.models.dataset import CleanedEvent, Dataset
from app.schemas.analytics import (
    ActivityReworkMetric,
    ActivityTimeMetric,
    BottleneckItem,
    BottlenecksResponse,
    CycleTimeDistributionBin,
    CycleTimeMetrics,
    DepartmentPerformanceItem,
    DepartmentPerformanceResponse,
    MonthlyTrendItem,
    OverviewMetrics,
    ReworkMetrics,
    TrendsResponse,
    VendorPerformanceItem,
    VendorPerformanceResponse,
    WaitingTimeMetrics,
)


# ── Helper: Percentiles Calculation ───────────────────────────────────────────

def calculate_percentile(sorted_values: List[float], percentile: float) -> float:
    """Calculates percentile from a sorted list of floats."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    k = (n - 1) * percentile
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_values[int(k)]
    d0 = sorted_values[int(f)] * (c - k)
    d1 = sorted_values[int(c)] * (k - f)
    return round(d0 + d1, 4)


# ── Service Methods ───────────────────────────────────────────────────────────

def get_overview_analytics(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sla_hours: float = 720.0,
) -> OverviewMetrics:
    """
    Overview operational analytics:
    - Total purchase cases
    - Total events
    - Completed vs incomplete cases (ensuring incomplete cases are not treated as completed)
    - Average, median, and P90 cycle times
    - Rework percentage
    - SLA breach percentage
    - Total spend
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise NotFoundError(f"Dataset '{dataset_id}' not found.")

    cases = fetch_case_durations_sql(db, dataset_id, start_date, end_date)
    total_cases = len(cases)

    # Event count
    q_events = db.query(func.count(CleanedEvent.id)).filter(CleanedEvent.dataset_id == dataset_id)
    if start_date:
        q_events = q_events.filter(CleanedEvent.timestamp >= start_date)
    if end_date:
        q_events = q_events.filter(CleanedEvent.timestamp <= end_date)
    total_events = q_events.scalar() or 0

    if total_cases == 0:
        return OverviewMetrics(
            dataset_id=dataset_id,
            total_purchase_cases=0,
            total_events=0,
            completed_cases=0,
            incomplete_cases=0,
            completion_rate=0.0,
            avg_cycle_time_hours=0.0,
            median_cycle_time_hours=0.0,
            p90_cycle_time_hours=0.0,
            rework_cases=0,
            rework_percentage=0.0,
            sla_hours=sla_hours,
            sla_breach_cases=0,
            sla_breach_percentage=0.0,
            total_spend_usd=0.0,
            start_date=start_date,
            end_date=end_date,
        )

    completed_cases = sum(1 for c in cases if c["is_completed"])
    incomplete_cases = total_cases - completed_cases
    completion_rate = round(completed_cases / total_cases, 4)

    # Cycle time: strictly for completed cases (fallback to all cases if none completed)
    duration_pool = [c["duration_hours"] for c in cases if c["is_completed"]]
    if not duration_pool:
        duration_pool = [c["duration_hours"] for c in cases]
    duration_pool.sort()

    avg_cycle = round(sum(duration_pool) / len(duration_pool), 2)
    med_cycle = calculate_percentile(duration_pool, 0.50)
    p90_cycle = calculate_percentile(duration_pool, 0.90)

    # SLA breaches
    sla_breaches = sum(1 for d in duration_pool if d > sla_hours)
    sla_pct = round(sla_breaches / len(duration_pool), 4)

    # Rework
    rework_rows = fetch_rework_sql(db, dataset_id, start_date, end_date)
    rework_cases_set = {r["case_id"] for r in rework_rows}
    rework_case_count = len(rework_cases_set)
    rework_pct = round(rework_case_count / total_cases, 4)

    # Total spend from attributes
    events = fetch_case_attributes_and_events(db, dataset_id, start_date, end_date)
    case_spends: Dict[str, float] = {}
    for ev in events:
        cid = ev["case_id"]
        if cid not in case_spends:
            amt = ev["extra_attributes"].get("amount") or ev["extra_attributes"].get("Amount USD") or 0.0
            try:
                case_spends[cid] = float(amt)
            except Exception:
                case_spends[cid] = 0.0

    total_spend = round(sum(case_spends.values()), 2)

    return OverviewMetrics(
        dataset_id=dataset_id,
        total_purchase_cases=total_cases,
        total_events=total_events,
        completed_cases=completed_cases,
        incomplete_cases=incomplete_cases,
        completion_rate=completion_rate,
        avg_cycle_time_hours=avg_cycle,
        median_cycle_time_hours=med_cycle,
        p90_cycle_time_hours=p90_cycle,
        rework_cases=rework_case_count,
        rework_percentage=rework_pct,
        sla_hours=sla_hours,
        sla_breach_cases=sla_breaches,
        sla_breach_percentage=sla_pct,
        total_spend_usd=total_spend,
        start_date=start_date,
        end_date=end_date,
    )


def get_cycle_time_analytics(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sla_hours: float = 720.0,
) -> CycleTimeMetrics:
    """
    Detailed cycle time analytics:
    Calculates average, median, P75, P90, P95, min, max, and frequency distribution bins.
    """
    cases = fetch_case_durations_sql(db, dataset_id, start_date, end_date)
    total_cases = len(cases)
    completed_cases = sum(1 for c in cases if c["is_completed"])

    if total_cases == 0:
        return CycleTimeMetrics(
            dataset_id=dataset_id,
            total_cases=0,
            completed_cases=0,
            avg_cycle_time_hours=0.0,
            median_cycle_time_hours=0.0,
            p75_cycle_time_hours=0.0,
            p90_cycle_time_hours=0.0,
            p95_cycle_time_hours=0.0,
            min_cycle_time_hours=0.0,
            max_cycle_time_hours=0.0,
            sla_hours=sla_hours,
            sla_breach_count=0,
            sla_breach_percentage=0.0,
            distribution=[],
        )

    # Use completed cases for accurate cycle time, fallback to all if zero completed
    duration_pool = [c["duration_hours"] for c in cases if c["is_completed"]]
    if not duration_pool:
        duration_pool = [c["duration_hours"] for c in cases]
    duration_pool.sort()

    avg_ct = round(sum(duration_pool) / len(duration_pool), 2)
    med_ct = calculate_percentile(duration_pool, 0.50)
    p75_ct = calculate_percentile(duration_pool, 0.75)
    p90_ct = calculate_percentile(duration_pool, 0.90)
    p95_ct = calculate_percentile(duration_pool, 0.95)
    min_ct = duration_pool[0]
    max_ct = duration_pool[-1]

    sla_breaches = sum(1 for d in duration_pool if d > sla_hours)
    sla_pct = round(sla_breaches / len(duration_pool), 4)

    # Build histogram distribution (10 bins)
    num_bins = 10
    bin_width = (max_ct - min_ct) / num_bins if max_ct > min_ct else 1.0
    bins: List[CycleTimeDistributionBin] = []

    for i in range(num_bins):
        b_start = round(min_ct + i * bin_width, 2)
        b_end = round(min_ct + (i + 1) * bin_width, 2)
        count = sum(1 for d in duration_pool if (b_start <= d < b_end) or (i == num_bins - 1 and d == max_ct))
        bins.append(CycleTimeDistributionBin(bin_start_hours=b_start, bin_end_hours=b_end, case_count=count))

    return CycleTimeMetrics(
        dataset_id=dataset_id,
        total_cases=total_cases,
        completed_cases=completed_cases,
        avg_cycle_time_hours=avg_ct,
        median_cycle_time_hours=med_ct,
        p75_cycle_time_hours=p75_ct,
        p90_cycle_time_hours=p90_ct,
        p95_cycle_time_hours=p95_ct,
        min_cycle_time_hours=min_ct,
        max_cycle_time_hours=max_ct,
        sla_hours=sla_hours,
        sla_breach_count=sla_breaches,
        sla_breach_percentage=sla_pct,
        distribution=bins,
    )


def get_waiting_time_analytics(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> WaitingTimeMetrics:
    """
    Computes per-activity waiting time using consecutive event timestamps.
    Ranks activities by average waiting time.
    """
    transitions = fetch_activity_transitions_sql(db, dataset_id, start_date, end_date)
    if not transitions:
        return WaitingTimeMetrics(
            dataset_id=dataset_id,
            overall_avg_waiting_time_hours=0.0,
            activities=[],
        )

    grouped: Dict[str, List[float]] = defaultdict(list)
    for t in transitions:
        grouped[t["activity"]].append(t["waiting_time_hours"])

    all_times = [t["waiting_time_hours"] for t in transitions]
    overall_avg = round(sum(all_times) / len(all_times), 2)

    activity_metrics: List[ActivityTimeMetric] = []
    for act, times in grouped.items():
        times.sort()
        avg_w = round(sum(times) / len(times), 2)
        med_w = calculate_percentile(times, 0.50)
        p90_w = calculate_percentile(times, 0.90)
        tot_w = round(sum(times), 2)

        activity_metrics.append(ActivityTimeMetric(
            activity=act,
            transition_count=len(times),
            avg_waiting_time_hours=avg_w,
            median_waiting_time_hours=med_w,
            p90_waiting_time_hours=p90_w,
            min_waiting_time_hours=times[0],
            max_waiting_time_hours=times[-1],
            total_waiting_time_hours=tot_w,
        ))

    # Rank descending by average waiting time
    activity_metrics.sort(key=lambda x: x.avg_waiting_time_hours, reverse=True)

    return WaitingTimeMetrics(
        dataset_id=dataset_id,
        overall_avg_waiting_time_hours=overall_avg,
        activities=activity_metrics,
    )


def get_rework_analytics(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> ReworkMetrics:
    """
    Rework calculation:
    Identifies repeated execution of activities within the same case.
    """
    cases = fetch_case_durations_sql(db, dataset_id, start_date, end_date)
    total_cases = len(cases)

    rework_rows = fetch_rework_sql(db, dataset_id, start_date, end_date)
    if total_cases == 0 or not rework_rows:
        return ReworkMetrics(
            dataset_id=dataset_id,
            total_cases=total_cases,
            cases_with_rework=0,
            rework_case_percentage=0.0,
            total_rework_events=0,
            activities=[],
        )

    cases_with_rework = len({r["case_id"] for r in rework_rows})
    total_rework_events = sum(r["rework_count"] for r in rework_rows)
    pct = round(cases_with_rework / total_cases, 4)

    # Group by activity
    act_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"rework_cases": 0, "total_rework": 0, "max_rep": 0})
    for r in rework_rows:
        act = r["activity"]
        act_stats[act]["rework_cases"] += 1
        act_stats[act]["total_rework"] += r["rework_count"]
        act_stats[act]["max_rep"] = max(act_stats[act]["max_rep"], r["execution_count"])

    activity_rework: List[ActivityReworkMetric] = []
    for act, s in act_stats.items():
        rate = round(s["rework_cases"] / total_cases, 4)
        activity_rework.append(ActivityReworkMetric(
            activity=act,
            rework_case_count=s["rework_cases"],
            total_rework_occurrences=s["total_rework"],
            rework_rate=rate,
            max_repetitions_in_case=s["max_rep"],
        ))

    activity_rework.sort(key=lambda x: x.rework_case_count, reverse=True)

    return ReworkMetrics(
        dataset_id=dataset_id,
        total_cases=total_cases,
        cases_with_rework=cases_with_rework,
        rework_case_percentage=pct,
        total_rework_events=total_rework_events,
        activities=activity_rework,
    )


def get_bottleneck_analytics(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    activity_sla_hours: float = 48.0,
) -> BottlenecksResponse:
    """
    Bottleneck identification & explainable ranking:
    Calculates composite score based on:
      1. Average waiting time (40% weight)
      2. Median waiting time (20% weight)
      3. Rework repetition rate (20% weight)
      4. Transition SLA breach rate (20% weight)
    Produces transparent explanation reasons.
    """
    wt_metrics = get_waiting_time_analytics(db, dataset_id, start_date, end_date)
    rework_metrics = get_rework_analytics(db, dataset_id, start_date, end_date)
    transitions = fetch_activity_transitions_sql(db, dataset_id, start_date, end_date)

    if not wt_metrics.activities:
        return BottlenecksResponse(
            dataset_id=dataset_id,
            top_bottleneck=None,
            ranking_methodology=(
                "Score = (WaitTimeNorm * 0.40) + (MedianWaitNorm * 0.20) + (ReworkRate * 0.20) + (SlaBreachRate * 0.20)"
            ),
            bottlenecks=[],
        )

    rework_map = {a.activity: a for a in rework_metrics.activities}

    # Transition SLA breaches per activity
    trans_by_act: Dict[str, List[float]] = defaultdict(list)
    cases_by_act: Dict[str, set] = defaultdict(set)
    for t in transitions:
        trans_by_act[t["activity"]].append(t["waiting_time_hours"])
        cases_by_act[t["activity"]].add(t["case_id"])

    sla_breach_map: Dict[str, float] = {}
    for act, times in trans_by_act.items():
        breaches = sum(1 for tm in times if tm > activity_sla_hours)
        sla_breach_map[act] = round(breaches / len(times), 4) if times else 0.0

    max_avg_wait = max((a.avg_waiting_time_hours for a in wt_metrics.activities), default=1.0) or 1.0
    max_med_wait = max((a.median_waiting_time_hours for a in wt_metrics.activities), default=1.0) or 1.0

    items: List[BottleneckItem] = []
    for a in wt_metrics.activities:
        act = a.activity
        avg_wait = a.avg_waiting_time_hours
        med_wait = a.median_waiting_time_hours

        # Normalized waiting times [0, 1]
        norm_avg = min(1.0, avg_wait / max_avg_wait)
        norm_med = min(1.0, med_wait / max_med_wait)

        rew = rework_map.get(act)
        rew_rate = rew.rework_rate if rew else 0.0
        breach_rate = sla_breach_map.get(act, 0.0)

        # Composite score on a 0-100 scale
        score = round((norm_avg * 40.0) + (norm_med * 20.0) + (rew_rate * 20.0 * 100.0) + (breach_rate * 20.0 * 100.0), 2)

        # Explainable reasons
        reasons: List[str] = []
        if norm_avg >= 0.7:
            reasons.append(f"High average waiting time: {avg_wait:.1f} hrs (top tier)")
        elif avg_wait > 24.0:
            reasons.append(f"Significant waiting time: {avg_wait:.1f} hrs")

        if rew_rate > 0.05:
            reasons.append(f"Frequent rework: repeated in {rew_rate * 100:.1f}% of cases")

        if breach_rate > 0.10:
            reasons.append(f"Activity transition SLA ({activity_sla_hours}h) breached in {breach_rate * 100:.1f}% of occurrences")

        if not reasons:
            reasons.append(f"Average waiting time: {avg_wait:.1f} hrs across {a.transition_count} transitions")

        items.append(BottleneckItem(
            rank=0,  # set below
            activity=act,
            bottleneck_score=score,
            avg_waiting_time_hours=avg_wait,
            median_waiting_time_hours=med_wait,
            rework_rate=rew_rate,
            sla_breach_rate=breach_rate,
            transition_count=a.transition_count,
            affected_case_count=len(cases_by_act.get(act, set())),
            reasons=reasons,
        ))

    # Rank by composite bottleneck_score descending
    items.sort(key=lambda x: x.bottleneck_score, reverse=True)
    for idx, item in enumerate(items, start=1):
        item.rank = idx

    top = items[0].activity if items else None

    return BottlenecksResponse(
        dataset_id=dataset_id,
        top_bottleneck=top,
        ranking_methodology=(
            "Score = (WaitTimeNorm * 40) + (MedianWaitNorm * 20) + (ReworkRate * 2000) + (SlaBreachRate * 2000). "
            "Evaluates queueing delays, process looping, and SLA non-compliance."
        ),
        bottlenecks=items,
    )


def get_vendor_performance_analytics(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    sla_hours: float = 720.0,
) -> VendorPerformanceResponse:
    """
    Multidimensional vendor analytics:
    Cycle times, total spend, SLA breach rates, and completion rates by vendor.
    """
    cases = fetch_case_durations_sql(db, dataset_id, start_date, end_date)
    case_dur_map = {c["case_id"]: c for c in cases}

    events = fetch_case_attributes_and_events(db, dataset_id, start_date, end_date)

    # Associate each case with vendor and spend
    case_meta: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"vendor_id": "Unassigned", "amount": 0.0})
    for ev in events:
        cid = ev["case_id"]
        v = ev["extra_attributes"].get("vendor_id") or ev["extra_attributes"].get("Vendor ID")
        amt = ev["extra_attributes"].get("amount") or ev["extra_attributes"].get("Amount USD") or 0.0

        if v and case_meta[cid]["vendor_id"] == "Unassigned":
            case_meta[cid]["vendor_id"] = str(v)
        if amt and case_meta[cid]["amount"] == 0.0:
            try:
                case_meta[cid]["amount"] = float(amt)
            except Exception:
                pass

    # Group cases by vendor
    vendor_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for cid, c_data in case_dur_map.items():
        v_id = case_meta[cid]["vendor_id"]
        c_item = {**c_data, "amount": case_meta[cid]["amount"]}
        vendor_groups[v_id].append(c_item)

    items: List[VendorPerformanceItem] = []
    for vid, c_list in vendor_groups.items():
        total_c = len(c_list)
        total_spend = round(sum(c["amount"] for c in c_list), 2)
        durations = [c["duration_hours"] for c in c_list]
        durations.sort()

        avg_ct = round(sum(durations) / len(durations), 2)
        med_ct = calculate_percentile(durations, 0.50)

        sla_breaches = sum(1 for d in durations if d > sla_hours)
        sla_rate = round(sla_breaches / total_c, 4)

        completed = sum(1 for c in c_list if c["is_completed"])
        comp_rate = round(completed / total_c, 4)

        items.append(VendorPerformanceItem(
            vendor_id=vid,
            total_cases=total_c,
            total_spend_usd=total_spend,
            avg_cycle_time_hours=avg_ct,
            median_cycle_time_hours=med_ct,
            sla_breach_count=sla_breaches,
            sla_breach_rate=sla_rate,
            completed_cases=completed,
            completion_rate=comp_rate,
        ))

    items.sort(key=lambda x: x.total_cases, reverse=True)

    return VendorPerformanceResponse(
        dataset_id=dataset_id,
        total_vendors=len(items),
        vendors=items,
    )


def get_department_performance_analytics(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> DepartmentPerformanceResponse:
    """
    Departmental analytics:
    Spend, cycle time, rework rates, and completion rates by department.
    """
    cases = fetch_case_durations_sql(db, dataset_id, start_date, end_date)
    case_dur_map = {c["case_id"]: c for c in cases}

    rework_rows = fetch_rework_sql(db, dataset_id, start_date, end_date)
    rework_cases_set = {r["case_id"] for r in rework_rows}

    events = fetch_case_attributes_and_events(db, dataset_id, start_date, end_date)

    case_meta: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"department": "Unassigned", "amount": 0.0})
    for ev in events:
        cid = ev["case_id"]
        dept = ev["extra_attributes"].get("department") or ev["extra_attributes"].get("Department")
        amt = ev["extra_attributes"].get("amount") or ev["extra_attributes"].get("Amount USD") or 0.0

        if dept and case_meta[cid]["department"] == "Unassigned":
            case_meta[cid]["department"] = str(dept)
        if amt and case_meta[cid]["amount"] == 0.0:
            try:
                case_meta[cid]["amount"] = float(amt)
            except Exception:
                pass

    dept_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for cid, c_data in case_dur_map.items():
        dept = case_meta[cid]["department"]
        dept_groups[dept].append({
            **c_data,
            "amount": case_meta[cid]["amount"],
            "has_rework": cid in rework_cases_set,
        })

    items: List[DepartmentPerformanceItem] = []
    for dept, c_list in dept_groups.items():
        total_c = len(c_list)
        total_spend = round(sum(c["amount"] for c in c_list), 2)
        durations = [c["duration_hours"] for c in c_list]
        durations.sort()
        avg_ct = round(sum(durations) / len(durations), 2)

        rework_c = sum(1 for c in c_list if c["has_rework"])
        rework_rate = round(rework_c / total_c, 4)

        completed = sum(1 for c in c_list if c["is_completed"])
        comp_rate = round(completed / total_c, 4)

        items.append(DepartmentPerformanceItem(
            department=dept,
            total_cases=total_c,
            total_spend_usd=total_spend,
            avg_cycle_time_hours=avg_ct,
            rework_cases=rework_c,
            rework_rate=rework_rate,
            completed_cases=completed,
            completion_rate=comp_rate,
        ))

    items.sort(key=lambda x: x.total_cases, reverse=True)

    return DepartmentPerformanceResponse(
        dataset_id=dataset_id,
        total_departments=len(items),
        departments=items,
    )


def get_trends_analytics(
    db: Session,
    dataset_id: uuid.UUID,
    sla_hours: float = 720.0,
) -> TrendsResponse:
    """
    Monthly transaction trends:
    Tracks volume, completion, spend, cycle time, and SLA breach rates over time.
    """
    cases = fetch_case_durations_sql(db, dataset_id)
    events = fetch_case_attributes_and_events(db, dataset_id)

    # Get case amounts
    case_amounts: Dict[str, float] = {}
    for ev in events:
        cid = ev["case_id"]
        if cid not in case_amounts:
            amt = ev["extra_attributes"].get("amount") or ev["extra_attributes"].get("Amount USD") or 0.0
            try:
                case_amounts[cid] = float(amt)
            except Exception:
                case_amounts[cid] = 0.0

    # Group by case start month
    month_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for c in cases:
        min_ts = c["min_ts"]
        if min_ts:
            m_str = min_ts.strftime("%Y-%m")
            month_groups[m_str].append({
                **c,
                "amount": case_amounts.get(c["case_id"], 0.0),
            })

    # Group events by month for total_events
    month_events: Dict[str, int] = defaultdict(int)
    for ev in events:
        ts = ev["timestamp"]
        if ts:
            m_str = ts.strftime("%Y-%m")
            month_events[m_str] += 1

    sorted_months = sorted(month_groups.keys())
    trend_items: List[MonthlyTrendItem] = []

    for m in sorted_months:
        c_list = month_groups[m]
        vol = len(c_list)
        comp = sum(1 for c in c_list if c["is_completed"])
        spend = round(sum(c["amount"] for c in c_list), 2)
        durations = [c["duration_hours"] for c in c_list]
        avg_ct = round(sum(durations) / len(durations), 2) if durations else 0.0

        breaches = sum(1 for d in durations if d > sla_hours)
        breach_rate = round(breaches / vol, 4) if vol else 0.0

        trend_items.append(MonthlyTrendItem(
            month=m,
            case_volume=vol,
            completed_cases=comp,
            total_events=month_events.get(m, 0),
            total_spend_usd=spend,
            avg_cycle_time_hours=avg_ct,
            sla_breach_rate=breach_rate,
        ))

    return TrendsResponse(
        dataset_id=dataset_id,
        trends=trend_items,
    )
