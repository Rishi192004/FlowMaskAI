"""
FlowMind — Grounded AI & Recommendations Package.
"""
from app.ai.assistant import answer_assistant_query, classify_assistant_intent
from app.ai.engine import generate_recommendations
from app.ai.rules import (
    evaluate_approval_bottleneck,
    evaluate_early_invoice,
    evaluate_high_abandonment,
    evaluate_high_rework,
    evaluate_low_fpy,
    evaluate_skip_approval,
    evaluate_skip_verification,
    evaluate_sla_breach,
)
from app.schemas.ai import (
    RecommendationCategoryEnum,
    RecommendationItem,
    RecommendationsConfig,
    RecommendationsResponse,
    RecommendationSeverityEnum,
)

__all__ = [
    "answer_assistant_query",
    "classify_assistant_intent",
    "generate_recommendations",
    "RecommendationsConfig",
    "RecommendationItem",
    "RecommendationsResponse",
    "RecommendationCategoryEnum",
    "RecommendationSeverityEnum",
    "evaluate_skip_approval",
    "evaluate_early_invoice",
    "evaluate_skip_verification",
    "evaluate_high_rework",
    "evaluate_approval_bottleneck",
    "evaluate_low_fpy",
    "evaluate_high_abandonment",
    "evaluate_sla_breach",
]
