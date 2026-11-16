"""
Pydantic schemas for Process Mining, DFG, Variants, Process Map,
Inductive Miner discovery, and Process Comparison.
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field


# ── Process Map (React Flow compatible) ───────────────────────────────────────

class ProcessMapNode(BaseModel):
    id: str
    label: str
    frequency: int
    avg_duration_hours: float = 0.0
    is_start: bool = False
    is_end: bool = False
    is_bottleneck: bool = False


class ProcessMapEdge(BaseModel):
    id: str
    source: str
    target: str
    frequency: int
    avg_duration_hours: float = 0.0
    median_duration_hours: float = 0.0
    is_bottleneck: bool = False


class ProcessMapResponse(BaseModel):
    dataset_id: uuid.UUID
    total_cases: int
    total_events: int
    nodes: List[ProcessMapNode]
    edges: List[ProcessMapEdge]
    start_activities: Dict[str, int]
    end_activities: Dict[str, int]


# ── DFG (Directly-Follows Graph) ─────────────────────────────────────────────

class DFGTransition(BaseModel):
    source: str
    target: str
    frequency: int
    avg_duration_hours: float


class DFGResponse(BaseModel):
    dataset_id: uuid.UUID
    total_cases: int
    total_events: int
    transitions: List[DFGTransition]
    start_activities: Dict[str, int]
    end_activities: Dict[str, int]


# ── Process Discovery (Inductive Miner / Petri Net) ───────────────────────────

class PetriNetPlace(BaseModel):
    id: str
    name: str


class PetriNetTransition(BaseModel):
    id: str
    label: Optional[str] = None


class PetriNetArc(BaseModel):
    source: str
    target: str


class ProcessDiscoveryResponse(BaseModel):
    dataset_id: uuid.UUID
    algorithm: str  # "inductive"
    places: List[PetriNetPlace]
    transitions: List[PetriNetTransition]
    arcs: List[PetriNetArc]
    start_activities: Dict[str, int]
    end_activities: Dict[str, int]
    process_tree_repr: Optional[str] = None


# ── Process Variants ──────────────────────────────────────────────────────────

class ProcessVariantItem(BaseModel):
    variant_id: int
    activities: List[str]
    variant_signature: str
    case_count: int
    percentage: float
    is_rare: bool
    sample_case_ids: List[str]


class ProcessVariantsResponse(BaseModel):
    dataset_id: uuid.UUID
    total_cases: int
    unique_variants_count: int
    top_variant_percentage: float
    variants: List[ProcessVariantItem]
    excessive_activity_cases: List[Dict[str, Any]]


# ── Activity Frequency Analysis ───────────────────────────────────────────────

class ActivityFrequencyItem(BaseModel):
    activity: str
    event_count: int
    case_count: int
    case_coverage_percentage: float
    is_start: bool
    is_end: bool


class ActivityFrequencyResponse(BaseModel):
    dataset_id: uuid.UUID
    total_events: int
    total_cases: int
    activities: List[ActivityFrequencyItem]


# ── Process Comparison ────────────────────────────────────────────────────────

class ComparisonSliceMetrics(BaseModel):
    label: str
    case_count: int
    event_count: int
    unique_variants: int
    avg_cycle_time_hours: float
    top_variant: Optional[str] = None


class ComparisonResponse(BaseModel):
    dataset_id: uuid.UUID
    slice_a: ComparisonSliceMetrics
    slice_b: ComparisonSliceMetrics
    shared_activities: List[str]
    unique_to_a: List[str]
    unique_to_b: List[str]
    divergence_summary: str
