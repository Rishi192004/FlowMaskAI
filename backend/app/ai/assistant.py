"""Intent classification and evidence assembly for the process assistant."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.ai.engine import generate_recommendations
from app.ai.llm import AssistantGenerationError, generate_grounded_answer
from app.analytics.service import (
    get_bottleneck_analytics,
    get_overview_analytics,
    get_rework_analytics,
    get_vendor_performance_analytics,
)
from app.conformance.engine import get_conformance_overview_response
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models.dataset import Dataset
from app.schemas.ai import (
    AssistantIntentEnum,
    AssistantMetricFact,
    AssistantQueryRequest,
    AssistantQueryResponse,
    RecommendationItem,
)

logger = logging.getLogger(__name__)


def classify_assistant_intent(question: str) -> AssistantIntentEnum:
    """Map supported questions to fixed analytics workflows, never to SQL."""
    query = " ".join(question.casefold().split())

    if any(term in query for term in ("prioritize", "prioritise", "management action", "what actions")):
        return AssistantIntentEnum.PRIORITIES
    if any(term in query for term in ("vendor", "supplier")) and any(
        term in query for term in ("sla", "breach", "rate", "highest", "performance")
    ):
        return AssistantIntentEnum.VENDOR_SLA
    if any(term in query for term in ("rework", "repeated activit", "repeat activity")):
        return AssistantIntentEnum.REWORK
    if any(
        term in query
        for term in ("reference process", "conformance", "violate", "deviation", "compliance")
    ):
        return AssistantIntentEnum.CONFORMANCE
    if "bottleneck" in query:
        return AssistantIntentEnum.BOTTLENECK
    if any(
        term in query
        for term in ("longer than expected", "cycle time", "taking longer", "slow", "duration")
    ):
        return AssistantIntentEnum.CYCLE_TIME
    return AssistantIntentEnum.UNSUPPORTED


def _is_greeting(question: str) -> bool:
    normalized = " ".join(question.casefold().split()).strip("!.,?")
    return normalized in {
        "hi",
        "hello",
        "hey",
        "hi flowmind",
        "hello flowmind",
        "good morning",
        "good afternoon",
        "good evening",
    }


def _fact(
    key: str,
    label: str,
    value: str | int | float,
    display_value: str,
    source: str,
) -> AssistantMetricFact:
    return AssistantMetricFact(
        key=key,
        label=label,
        value=value,
        display_value=display_value,
        source=source,
    )


def _unavailable_response(
    dataset_id: uuid.UUID,
    intent: AssistantIntentEnum,
    message: str,
) -> AssistantQueryResponse:
    return AssistantQueryResponse(
        dataset_id=dataset_id,
        intent=intent,
        answer=message,
        available=False,
        measured_facts=[],
        configured_baselines=[],
        recommendations=[],
    )


def _generate_response(
    request: AssistantQueryRequest,
    intent: AssistantIntentEnum,
    facts: List[AssistantMetricFact],
    baselines: List[AssistantMetricFact],
    recommendations: List[RecommendationItem],
) -> AssistantQueryResponse:
    try:
        answer = generate_grounded_answer(
            request.question,
            intent.value,
            facts,
            baselines,
            recommendations,
        )
        generation_model = settings.OLLAMA_MODEL
    except AssistantGenerationError as exc:
        logger.warning("Could not generate grounded assistant narrative: %s", exc)
        answer = (
            "The measured facts and recommendations are available below, but the "
            "local model could not provide a safe narrative."
        )
        generation_model = None

    return AssistantQueryResponse(
        dataset_id=request.dataset_id,
        intent=intent,
        answer=answer,
        available=True,
        measured_facts=facts,
        configured_baselines=baselines,
        recommendations=recommendations,
        generation_model=generation_model,
    )


def answer_assistant_query(
    db: Session,
    request: AssistantQueryRequest,
) -> AssistantQueryResponse:
    """Classify a user question and respond from existing analytical services."""
    intent = classify_assistant_intent(request.question)
    if not db.query(Dataset.id).filter(Dataset.id == request.dataset_id).first():
        raise NotFoundError(f"Dataset '{request.dataset_id}' not found.")

    if intent == AssistantIntentEnum.UNSUPPORTED:
        if _is_greeting(request.question):
            return _unavailable_response(
                request.dataset_id,
                intent,
                "Hi! I can help analyze this process dataset. Try asking about bottlenecks, "
                "vendor SLA breaches, cycle time, rework, conformance, or management priorities.",
            )
        return _unavailable_response(
            request.dataset_id,
            intent,
            "I can't answer that from the available process analytics. Try asking about bottlenecks, "
            "vendor SLA breaches, cycle time, rework, conformance, or management priorities.",
        )

    config = request.recommendations_config
    start_date: datetime | None = request.start_date
    end_date: datetime | None = request.end_date

    if intent == AssistantIntentEnum.PRIORITIES:
        result = generate_recommendations(
            db,
            request.dataset_id,
            config=config,
            start_date=start_date,
            end_date=end_date,
        )
        if result.total_cases_analyzed == 0:
            return _unavailable_response(
                request.dataset_id,
                intent,
                "There are no purchase cases in the selected dataset and date range to prioritize.",
            )
        facts = [
            _fact(
                "priorities.total_cases",
                "Total analyzed cases",
                result.total_cases_analyzed,
                str(result.total_cases_analyzed),
                "recommendations.summary",
            ),
            _fact(
                "priorities.recommendation_count",
                "Triggered recommendations",
                result.recommendations_count,
                str(result.recommendations_count),
                "recommendations.summary",
            ),
        ]
        return _generate_response(request, intent, facts, [], result.recommendations)

    overview = get_overview_analytics(
        db,
        request.dataset_id,
        start_date=start_date,
        end_date=end_date,
        sla_hours=config.sla_hours,
    )
    if overview.total_purchase_cases == 0:
        return _unavailable_response(
            request.dataset_id,
            intent,
            "There are no purchase cases in the selected dataset and date range to answer this question.",
        )

    facts: List[AssistantMetricFact] = []
    baselines: List[AssistantMetricFact] = []
    recommendations: List[RecommendationItem] = []

    if intent == AssistantIntentEnum.BOTTLENECK:
        result = get_bottleneck_analytics(
            db, request.dataset_id, start_date=start_date, end_date=end_date
        )
        if not result.bottlenecks:
            return _unavailable_response(
                request.dataset_id,
                intent,
                "No activity-transition measurements are available to identify a bottleneck.",
            )
        for item in result.bottlenecks[:5]:
            prefix = f"bottleneck.{item.rank}"
            facts.extend(
                [
                    _fact(
                        f"{prefix}.activity",
                        f"Rank {item.rank} activity",
                        item.activity,
                        item.activity,
                        "analytics.bottlenecks",
                    ),
                    _fact(
                        f"{prefix}.average_wait_hours",
                        f"{item.activity} average transition time",
                        item.avg_waiting_time_hours,
                        f"{item.avg_waiting_time_hours:.2f} hours",
                        "analytics.bottlenecks",
                    ),
                    _fact(
                        f"{prefix}.affected_cases",
                        f"{item.activity} cases",
                        item.affected_case_count,
                        str(item.affected_case_count),
                        "analytics.bottlenecks",
                    ),
                ]
            )
    elif intent == AssistantIntentEnum.VENDOR_SLA:
        result = get_vendor_performance_analytics(
            db,
            request.dataset_id,
            start_date=start_date,
            end_date=end_date,
            sla_hours=config.sla_hours,
        )
        vendors = sorted(
            result.vendors,
            key=lambda item: (item.sla_breach_rate, item.sla_breach_count),
            reverse=True,
        )
        assigned_vendors = [item for item in vendors if item.vendor_id != "Unassigned"]
        if not assigned_vendors:
            return _unavailable_response(
                request.dataset_id,
                intent,
                "Vendor-level SLA results are unavailable because the selected event data has no assigned vendor identifiers.",
            )
        for rank, item in enumerate(assigned_vendors[:5], start=1):
            prefix = f"vendor_sla.{rank}"
            facts.extend(
                [
                    _fact(
                        f"{prefix}.vendor_id",
                        f"Rank {rank} vendor",
                        item.vendor_id,
                        item.vendor_id,
                        "analytics.vendor_performance",
                    ),
                    _fact(
                        f"{prefix}.breach_rate",
                        f"{item.vendor_id} SLA breach rate",
                        item.sla_breach_rate,
                        f"{item.sla_breach_rate * 100:.2f}%",
                        "analytics.vendor_performance",
                    ),
                    _fact(
                        f"{prefix}.breach_cases",
                        f"{item.vendor_id} breached cases",
                        item.sla_breach_count,
                        f"{item.sla_breach_count} of {item.total_cases} cases",
                        "analytics.vendor_performance",
                    ),
                ]
            )
        baselines.append(
            _fact(
                "vendor_sla.target_hours",
                "Configured cycle-time target",
                config.sla_hours,
                f"{config.sla_hours:g} hours",
                "assistant.request.recommendations_config.sla_hours",
            )
        )

    elif intent == AssistantIntentEnum.CYCLE_TIME:
        facts.extend(
            [
                _fact(
                    "cycle_time.average_hours",
                    "Average observed cycle time",
                    overview.avg_cycle_time_hours,
                    f"{overview.avg_cycle_time_hours:.2f} hours",
                    "analytics.overview",
                ),
                _fact(
                    "cycle_time.p90_hours",
                    "P90 observed cycle time",
                    overview.p90_cycle_time_hours,
                    f"{overview.p90_cycle_time_hours:.2f} hours",
                    "analytics.overview",
                ),
                _fact(
                    "cycle_time.sla_breach_rate",
                    "SLA breach rate in the cycle-time measurement population",
                    overview.sla_breach_percentage,
                    f"{overview.sla_breach_percentage * 100:.2f}%",
                    "analytics.overview",
                ),
                _fact(
                    "cycle_time.sla_breach_cases",
                    "Cases over the configured cycle-time target",
                    overview.sla_breach_cases,
                    str(overview.sla_breach_cases),
                    "analytics.overview",
                ),
            ]
        )
        baselines.append(
            _fact(
                "cycle_time.sla_target_hours",
                "Configured cycle-time target",
                config.sla_hours,
                f"{config.sla_hours:g} hours",
                "assistant.request.recommendations_config.sla_hours",
            )
        )
        bottlenecks = get_bottleneck_analytics(
            db, request.dataset_id, start_date=start_date, end_date=end_date
        )
        for item in bottlenecks.bottlenecks[:3]:
            facts.append(
                _fact(
                    f"cycle_time.delay_activity.{item.rank}",
                    f"High-delay activity {item.rank}",
                    item.activity,
                    f"{item.activity}: {item.avg_waiting_time_hours:.2f} hours average transition time",
                    "analytics.bottlenecks",
                )
            )

    elif intent == AssistantIntentEnum.REWORK:
        result = get_rework_analytics(
            db, request.dataset_id, start_date=start_date, end_date=end_date
        )
        if not result.activities:
            facts.append(
                _fact(
                    "rework.total_rework_cases",
                    "Cases with repeated activities",
                    0,
                    "0",
                    "analytics.rework",
                )
            )
        else:
            for rank, item in enumerate(result.activities[:5], start=1):
                prefix = f"rework.{rank}"
                facts.extend(
                    [
                        _fact(
                            f"{prefix}.activity",
                            f"Rank {rank} repeated activity",
                            item.activity,
                            item.activity,
                            "analytics.rework",
                        ),
                        _fact(
                            f"{prefix}.case_count",
                            f"{item.activity} rework cases",
                            item.rework_case_count,
                            str(item.rework_case_count),
                            "analytics.rework",
                        ),
                        _fact(
                            f"{prefix}.repeat_occurrences",
                            f"{item.activity} repeated executions",
                            item.total_rework_occurrences,
                            str(item.total_rework_occurrences),
                            "analytics.rework",
                        ),
                    ]
                )
        facts.extend(
            [
                _fact(
                    "rework.total_cases",
                    "Total analyzed cases",
                    result.total_cases,
                    str(result.total_cases),
                    "analytics.rework",
                ),
                _fact(
                    "rework.total_rework_events",
                    "Total repeated event executions",
                    result.total_rework_events,
                    str(result.total_rework_events),
                    "analytics.rework",
                ),
            ]
        )

    elif intent == AssistantIntentEnum.CONFORMANCE:
        result = get_conformance_overview_response(
            db,
            request.dataset_id,
            start_date=start_date,
            end_date=end_date,
        )
        violation_rate = (
            result.deviant_cases / result.total_cases if result.total_cases else 0.0
        )
        facts.extend(
            [
                _fact(
                    "conformance.total_cases",
                    "Total analyzed cases",
                    result.total_cases,
                    str(result.total_cases),
                    "conformance.overview",
                ),
                _fact(
                    "conformance.deviant_cases",
                    "Cases violating the configured reference process",
                    result.deviant_cases,
                    str(result.deviant_cases),
                    "conformance.overview",
                ),
                _fact(
                    "conformance.violation_rate",
                    "Reference-process violation rate",
                    violation_rate,
                    f"{violation_rate * 100:.2f}%",
                    "conformance.overview",
                ),
            ]
        )
        for item in result.deviation_breakdown:
            facts.append(
                _fact(
                    f"conformance.deviation.{item.deviation_type}",
                    f"{item.deviation_type} affected cases",
                    item.affected_cases,
                    f"{item.affected_cases} cases ({item.percentage_of_cases:.2f}%)",
                    "conformance.overview",
                )
            )

    return _generate_response(request, intent, facts, baselines, recommendations)
