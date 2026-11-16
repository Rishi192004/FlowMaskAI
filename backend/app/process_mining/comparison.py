"""
Process Comparison Engine.
Compares business workflows across departments, vendors, or time periods.
Identifies divergence in execution paths, cycle times, and activity sets.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from app.process_mining.variants import extract_variants
from app.schemas.process_mining import ComparisonResponse, ComparisonSliceMetrics


def compare_process_slices(
    dataset_id: uuid.UUID,
    records_a: List[Dict[str, Any]],
    label_a: str,
    records_b: List[Dict[str, Any]],
    label_b: str,
) -> ComparisonResponse:
    """
    Computes comparative statistics between two subsets of an event log.
    """
    def _slice_stats(recs: List[Dict[str, Any]], lbl: str) -> ComparisonSliceMetrics:
        if not recs:
            return ComparisonSliceMetrics(
                label=lbl,
                case_count=0,
                event_count=0,
                unique_variants=0,
                avg_cycle_time_hours=0.0,
                top_variant=None,
            )

        v_map, case_lengths = extract_variants(recs)
        total_c = len(case_lengths)
        sorted_v = sorted(v_map.items(), key=lambda x: len(x[1]), reverse=True)
        top_v = " → ".join(sorted_v[0][0]) if sorted_v else None

        # Cycle time per case
        cases_events = {}
        for r in recs:
            cases_events.setdefault(r["case:concept:name"], []).append(r["time:timestamp"])

        durations = []
        for cid, tms in cases_events.items():
            dur_h = (max(tms) - min(tms)).total_seconds() / 3600.0
            durations.append(dur_h)

        avg_dur = round(sum(durations) / len(durations), 2) if durations else 0.0

        return ComparisonSliceMetrics(
            label=lbl,
            case_count=total_c,
            event_count=len(recs),
            unique_variants=len(sorted_v),
            avg_cycle_time_hours=avg_dur,
            top_variant=top_v,
        )

    stats_a = _slice_stats(records_a, label_a)
    stats_b = _slice_stats(records_b, label_b)

    acts_a = {r["concept:name"] for r in records_a}
    acts_b = {r["concept:name"] for r in records_b}

    shared = sorted(list(acts_a.intersection(acts_b)))
    unique_a = sorted(list(acts_a - acts_b))
    unique_b = sorted(list(acts_b - acts_a))

    # Summary of divergence
    diff_ct = round(abs(stats_a.avg_cycle_time_hours - stats_b.avg_cycle_time_hours), 2)
    slower = label_a if stats_a.avg_cycle_time_hours > stats_b.avg_cycle_time_hours else label_b

    summary_parts = [
        f"Compared '{label_a}' ({stats_a.case_count} cases) vs '{label_b}' ({stats_b.case_count} cases).",
        f"'{slower}' has a longer average cycle time by {diff_ct} hours.",
        f"'{label_a}' has {stats_a.unique_variants} distinct variants, while '{label_b}' has {stats_b.unique_variants} variants.",
    ]
    if unique_a:
        summary_parts.append(f"Activities exclusive to '{label_a}': {', '.join(unique_a)}.")
    if unique_b:
        summary_parts.append(f"Activities exclusive to '{label_b}': {', '.join(unique_b)}.")

    return ComparisonResponse(
        dataset_id=dataset_id,
        slice_a=stats_a,
        slice_b=stats_b,
        shared_activities=shared,
        unique_to_a=unique_a,
        unique_to_b=unique_b,
        divergence_summary=" ".join(summary_parts),
    )
