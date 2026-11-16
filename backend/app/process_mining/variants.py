"""
Process Variant Discovery and Activity Frequency Analysis.
Identifies:
  - Unique execution paths (variants)
  - Most frequent variants and percentage coverage
  - Rare variants (outliers and deviant processes)
  - Cases with excessive activities / rework loops
  - Activity coverage across cases
"""
from __future__ import annotations

import statistics
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from app.schemas.process_mining import (
    ActivityFrequencyItem,
    ActivityFrequencyResponse,
    ProcessVariantItem,
    ProcessVariantsResponse,
)


def extract_variants(
    records: List[Dict[str, Any]]
) -> Tuple[Dict[Tuple[str, ...], List[str]], Dict[str, int]]:
    """
    Groups cases by their ordered sequence of activities.
    Returns:
      - variant_map: { (activity_tuple): [case_id_1, case_id_2, ...] }
      - case_lengths: { case_id: event_count }
    """
    cases_events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for rec in records:
        cases_events[rec["case:concept:name"]].append(rec)

    variant_map: Dict[Tuple[str, ...], List[str]] = defaultdict(list)
    case_lengths: Dict[str, int] = {}

    for cid, trace in cases_events.items():
        trace.sort(key=lambda x: x["time:timestamp"])
        act_seq = tuple(x["concept:name"] for x in trace)
        variant_map[act_seq].append(cid)
        case_lengths[cid] = len(trace)

    return variant_map, case_lengths


def get_variants_response(
    dataset_id: uuid.UUID, records: List[Dict[str, Any]]
) -> ProcessVariantsResponse:
    """Analyzes and ranks all unique process variants."""
    if not records:
        return ProcessVariantsResponse(
            dataset_id=dataset_id,
            total_cases=0,
            unique_variants_count=0,
            top_variant_percentage=0.0,
            variants=[],
            excessive_activity_cases=[],
        )

    variant_map, case_lengths = extract_variants(records)
    total_cases = len(case_lengths)

    # Sort variants descending by case count
    sorted_variants = sorted(variant_map.items(), key=lambda x: len(x[1]), reverse=True)

    variant_items: List[ProcessVariantItem] = []
    for idx, (act_tuple, cids) in enumerate(sorted_variants, start=1):
        count = len(cids)
        pct = round((count / total_cases) * 100.0, 2)
        # Mark as rare if under 3% of cases or single execution
        is_rare = (pct < 3.0) or (count == 1 and total_cases > 5)

        variant_items.append(ProcessVariantItem(
            variant_id=idx,
            activities=list(act_tuple),
            variant_signature=" → ".join(act_tuple),
            case_count=count,
            percentage=pct,
            is_rare=is_rare,
            sample_case_ids=cids[:5],
        ))

    top_pct = variant_items[0].percentage if variant_items else 0.0

    # Detect cases with excessive activities (length > mean + 2*std or > 10)
    lengths = list(case_lengths.values())
    avg_len = statistics.mean(lengths) if lengths else 0.0
    stdev_len = statistics.stdev(lengths) if len(lengths) > 1 else 0.0
    threshold = max(10, avg_len + 2.0 * stdev_len)

    excessive_cases: List[Dict[str, Any]] = []
    for cid, length in case_lengths.items():
        if length >= threshold:
            excessive_cases.append({
                "case_id": cid,
                "event_count": length,
                "threshold": round(threshold, 1),
                "reason": f"Case has {length} events, significantly above average ({avg_len:.1f} events)",
            })

    excessive_cases.sort(key=lambda x: x["event_count"], reverse=True)

    return ProcessVariantsResponse(
        dataset_id=dataset_id,
        total_cases=total_cases,
        unique_variants_count=len(sorted_variants),
        top_variant_percentage=top_pct,
        variants=variant_items,
        excessive_activity_cases=excessive_cases[:25],
    )


def get_activity_frequency_response(
    dataset_id: uuid.UUID, records: List[Dict[str, Any]]
) -> ActivityFrequencyResponse:
    """Analyzes occurrence counts and case coverage for every activity."""
    if not records:
        return ActivityFrequencyResponse(
            dataset_id=dataset_id,
            total_events=0,
            total_cases=0,
            activities=[],
        )

    act_event_counts: Dict[str, int] = defaultdict(int)
    act_case_sets: Dict[str, set] = defaultdict(set)
    first_acts = set()
    last_acts = set()

    cases: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in records:
        act = r["concept:name"]
        cid = r["case:concept:name"]
        act_event_counts[act] += 1
        act_case_sets[act].add(cid)
        cases[cid].append(r)

    total_cases = len(cases)

    for cid, trace in cases.items():
        trace.sort(key=lambda x: x["time:timestamp"])
        first_acts.add(trace[0]["concept:name"])
        last_acts.add(trace[-1]["concept:name"])

    items: List[ActivityFrequencyItem] = []
    for act, ev_count in act_event_counts.items():
        c_count = len(act_case_sets[act])
        coverage = round((c_count / total_cases) * 100.0, 2)

        items.append(ActivityFrequencyItem(
            activity=act,
            event_count=ev_count,
            case_count=c_count,
            case_coverage_percentage=coverage,
            is_start=act in first_acts,
            is_end=act in last_acts,
        ))

    items.sort(key=lambda x: x.event_count, reverse=True)

    return ActivityFrequencyResponse(
        dataset_id=dataset_id,
        total_events=len(records),
        total_cases=total_cases,
        activities=items,
    )
