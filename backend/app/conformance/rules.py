"""
Configurable Business Rules & Reference Process Definitions.
Allows administrators to define, inspect, and update expected process constraints.
"""
from __future__ import annotations

import uuid
from typing import Dict

from app.schemas.conformance import ConformanceRulesConfig


# Default P2P Reference Process Sequence
DEFAULT_P2P_SEQUENCE = [
    "Purchase Requisition",
    "Manager Approval",
    "Purchase Order Created",
    "Goods Received",
    "Invoice Received",
    "Invoice Verified",
    "Payment Completed",
]

# In-memory store for dataset-specific rule configurations
_DATASET_RULES_STORE: Dict[str, ConformanceRulesConfig] = {}


def get_conformance_rules(dataset_id: uuid.UUID) -> ConformanceRulesConfig:
    """Returns the active conformance rules for a dataset, or the standard defaults."""
    key = str(dataset_id)
    if key in _DATASET_RULES_STORE:
        return _DATASET_RULES_STORE[key]
    return ConformanceRulesConfig(reference_sequence=list(DEFAULT_P2P_SEQUENCE))


def update_conformance_rules(
    dataset_id: uuid.UUID, new_config: ConformanceRulesConfig
) -> ConformanceRulesConfig:
    """Updates the active conformance rules for a dataset."""
    key = str(dataset_id)
    _DATASET_RULES_STORE[key] = new_config
    return new_config
