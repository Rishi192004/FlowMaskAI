"""
Unit & Integration Tests for Grounded Recommendations Engine.
Validates all 8 recommendation rules against deterministic datasets.
Ensures zero metric fabrication and strict grounding in calculated data.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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
from app.models.dataset import CleanedEvent, Dataset
from app.schemas.ai import RecommendationsConfig
from app.schemas.analytics import (
    ActivityReworkMetric,
    ActivityTimeMetric,
    BottleneckItem,
    BottlenecksResponse,
    OverviewMetrics,
    ReworkMetrics,
)
from app.schemas.conformance import (
    ConformanceOverviewResponse,
    ConformanceRulesConfig,
    DeviationSummaryItem,
)


# ── 1. Unit Tests for Independent Rule Evaluators ─────────────────────────────

def test_evaluate_skip_approval_trigger():
    config = RecommendationsConfig(skip_approval_threshold=0.0)
    overview = OverviewMetrics(
        dataset_id=uuid.uuid4(),
        total_purchase_cases=100,
        total_events=700,
        completed_cases=90,
        incomplete_cases=10,
        completion_rate=0.90,
        avg_cycle_time_hours=120.0,
        median_cycle_time_hours=100.0,
        p90_cycle_time_hours=200.0,
        rework_cases=5,
        rework_percentage=0.05,
        sla_hours=720.0,
        sla_breach_cases=8,
        sla_breach_percentage=0.08,
        total_spend_usd=50000.0,
    )
    conformance = ConformanceOverviewResponse(
        dataset_id=overview.dataset_id,
        total_cases=100,
        conformant_cases=92,
        deviant_cases=8,
        conformance_percentage=92.0,
        average_fitness_score=0.94,
        deviation_breakdown=[
            DeviationSummaryItem(
                deviation_type="SKIPPED_APPROVAL",
                category="Compliance",
                severity="HIGH",
                affected_cases=8,
                percentage_of_cases=8.0,
                description="Purchase Order created without prior authorized Manager Approval.",
            )
        ],
        active_rules=ConformanceRulesConfig(),
    )

    rec = evaluate_skip_approval(conformance, overview, config)
    assert rec is not None
    assert rec.rule_id == "SKIP_APPROVAL"
    assert rec.category == "COMPLIANCE"
    assert rec.severity == "CRITICAL"  # > 5% triggers CRITICAL
    assert rec.affected_case_count == 8
    assert rec.affected_case_percentage == 8.0
    assert rec.actual_metric_value == 0.08
    assert "8 cases" in rec.evidence_and_explanation


def test_evaluate_skip_approval_suppressed_when_zero():
    config = RecommendationsConfig(skip_approval_threshold=0.0)
    overview = OverviewMetrics(
        dataset_id=uuid.uuid4(),
        total_purchase_cases=50,
        total_events=350,
        completed_cases=50,
        incomplete_cases=0,
        completion_rate=1.0,
        avg_cycle_time_hours=80.0,
        median_cycle_time_hours=75.0,
        p90_cycle_time_hours=110.0,
        rework_cases=0,
        rework_percentage=0.0,
        sla_hours=720.0,
        sla_breach_cases=0,
        sla_breach_percentage=0.0,
        total_spend_usd=10000.0,
    )
    conformance = ConformanceOverviewResponse(
        dataset_id=overview.dataset_id,
        total_cases=50,
        conformant_cases=50,
        deviant_cases=0,
        conformance_percentage=100.0,
        average_fitness_score=1.0,
        deviation_breakdown=[],
        active_rules=ConformanceRulesConfig(),
    )

    rec = evaluate_skip_approval(conformance, overview, config)
    assert rec is None


def test_evaluate_early_invoice():
    config = RecommendationsConfig(early_invoice_threshold=0.0)
    overview = OverviewMetrics(
        dataset_id=uuid.uuid4(),
        total_purchase_cases=200,
        total_events=1400,
        completed_cases=190,
        incomplete_cases=10,
        completion_rate=0.95,
        avg_cycle_time_hours=100.0,
        median_cycle_time_hours=90.0,
        p90_cycle_time_hours=180.0,
        rework_cases=10,
        rework_percentage=0.05,
        sla_hours=720.0,
        sla_breach_cases=5,
        sla_breach_percentage=0.025,
        total_spend_usd=80000.0,
    )
    conformance = ConformanceOverviewResponse(
        dataset_id=overview.dataset_id,
        total_cases=200,
        conformant_cases=194,
        deviant_cases=6,
        conformance_percentage=97.0,
        average_fitness_score=0.98,
        deviation_breakdown=[
            DeviationSummaryItem(
                deviation_type="EARLY_INVOICE_VERIFICATION",
                category="Financial Risk",
                severity="HIGH",
                affected_cases=6,
                percentage_of_cases=3.0,
                description="Invoice verified before goods receipt.",
            )
        ],
        active_rules=ConformanceRulesConfig(),
    )

    rec = evaluate_early_invoice(conformance, overview, config)
    assert rec is not None
    assert rec.rule_id == "EARLY_INVOICE"
    assert rec.category == "FINANCIAL_RISK"
    assert rec.severity == "HIGH"
    assert rec.affected_case_count == 6
    assert rec.affected_case_percentage == 3.0


def test_evaluate_skip_verification():
    config = RecommendationsConfig(skip_verification_threshold=0.0)
    overview = OverviewMetrics(
        dataset_id=uuid.uuid4(),
        total_purchase_cases=100,
        total_events=700,
        completed_cases=95,
        incomplete_cases=5,
        completion_rate=0.95,
        avg_cycle_time_hours=90.0,
        median_cycle_time_hours=85.0,
        p90_cycle_time_hours=150.0,
        rework_cases=4,
        rework_percentage=0.04,
        sla_hours=720.0,
        sla_breach_cases=2,
        sla_breach_percentage=0.02,
        total_spend_usd=30000.0,
    )
    conformance = ConformanceOverviewResponse(
        dataset_id=overview.dataset_id,
        total_cases=100,
        conformant_cases=96,
        deviant_cases=4,
        conformance_percentage=96.0,
        average_fitness_score=0.97,
        deviation_breakdown=[
            DeviationSummaryItem(
                deviation_type="SKIPPED_INVOICE_VERIFICATION",
                category="Compliance",
                severity="HIGH",
                affected_cases=4,
                percentage_of_cases=4.0,
                description="Payment executed without invoice verification.",
            )
        ],
        active_rules=ConformanceRulesConfig(),
    )

    rec = evaluate_skip_verification(conformance, overview, config)
    assert rec is not None
    assert rec.rule_id == "SKIP_VERIFICATION"
    assert rec.category == "COMPLIANCE"
    assert rec.affected_case_count == 4


def test_evaluate_high_rework():
    config = RecommendationsConfig(high_rework_threshold=0.08)
    overview = OverviewMetrics(
        dataset_id=uuid.uuid4(),
        total_purchase_cases=100,
        total_events=850,
        completed_cases=90,
        incomplete_cases=10,
        completion_rate=0.90,
        avg_cycle_time_hours=150.0,
        median_cycle_time_hours=120.0,
        p90_cycle_time_hours=250.0,
        rework_cases=14,
        rework_percentage=0.14,  # 14% > 8%
        sla_hours=720.0,
        sla_breach_cases=5,
        sla_breach_percentage=0.05,
        total_spend_usd=60000.0,
    )
    rework = ReworkMetrics(
        dataset_id=overview.dataset_id,
        total_cases=100,
        cases_with_rework=14,
        rework_case_percentage=0.14,
        total_rework_events=28,
        activities=[
            ActivityReworkMetric(
                activity="Manager Approval",
                rework_case_count=12,
                total_rework_occurrences=24,
                rework_rate=0.12,
                max_repetitions_in_case=3,
            )
        ],
    )

    rec = evaluate_high_rework(overview, rework, config)
    assert rec is not None
    assert rec.rule_id == "HIGH_REWORK"
    assert rec.category == "QUALITY"
    assert rec.affected_case_count == 14
    assert "Manager Approval" in rec.recommended_corrective_action


def test_evaluate_approval_bottleneck():
    config = RecommendationsConfig(approval_bottleneck_hours=24.0)
    overview = OverviewMetrics(
        dataset_id=uuid.uuid4(),
        total_purchase_cases=100,
        total_events=700,
        completed_cases=90,
        incomplete_cases=10,
        completion_rate=0.90,
        avg_cycle_time_hours=180.0,
        median_cycle_time_hours=140.0,
        p90_cycle_time_hours=280.0,
        rework_cases=5,
        rework_percentage=0.05,
        sla_hours=720.0,
        sla_breach_cases=6,
        sla_breach_percentage=0.06,
        total_spend_usd=40000.0,
    )
    bottlenecks = BottlenecksResponse(
        dataset_id=overview.dataset_id,
        top_bottleneck="Manager Approval",
        ranking_methodology="Composite delay and queue score",
        bottlenecks=[
            BottleneckItem(
                rank=1,
                activity="Manager Approval",
                bottleneck_score=85.2,
                avg_waiting_time_hours=54.5,  # 54.5h > 24.0h
                median_waiting_time_hours=48.0,
                rework_rate=0.05,
                sla_breach_rate=0.12,
                transition_count=95,
                affected_case_count=90,
                reasons=["High average waiting time", "Frequent transition delay"],
            )
        ],
    )

    rec = evaluate_approval_bottleneck(bottlenecks, overview, config)
    assert rec is not None
    assert rec.rule_id == "APPROVAL_BOTTLENECK"
    assert rec.category == "EFFICIENCY"
    assert rec.severity == "HIGH"  # > 48h triggers HIGH
    assert rec.actual_metric_value == 54.5
    assert rec.affected_case_count == 90


def test_evaluate_approval_bottleneck_ignores_unrelated_top_stage():
    overview = OverviewMetrics(
        dataset_id=uuid.uuid4(),
        total_purchase_cases=100,
        total_events=700,
        completed_cases=90,
        incomplete_cases=10,
        completion_rate=0.90,
        avg_cycle_time_hours=180.0,
        median_cycle_time_hours=140.0,
        p90_cycle_time_hours=280.0,
        rework_cases=5,
        rework_percentage=0.05,
        sla_hours=720.0,
        sla_breach_cases=6,
        sla_breach_percentage=0.06,
        total_spend_usd=40000.0,
    )
    bottlenecks = BottlenecksResponse(
        dataset_id=overview.dataset_id,
        top_bottleneck="Invoice Received",
        ranking_methodology="Composite delay and queue score",
        bottlenecks=[
            BottleneckItem(
                rank=1,
                activity="Invoice Received",
                bottleneck_score=85.2,
                avg_waiting_time_hours=54.5,
                median_waiting_time_hours=48.0,
                rework_rate=0.05,
                sla_breach_rate=0.12,
                transition_count=95,
                affected_case_count=90,
                reasons=["High average waiting time"],
            )
        ],
    )

    assert evaluate_approval_bottleneck(
        bottlenecks, overview, RecommendationsConfig(approval_bottleneck_hours=24.0)
    ) is None


def test_evaluate_low_fpy():
    config = RecommendationsConfig(low_fpy_threshold=0.80)
    overview = OverviewMetrics(
        dataset_id=uuid.uuid4(),
        total_purchase_cases=100,
        total_events=700,
        completed_cases=85,
        incomplete_cases=15,
        completion_rate=0.85,
        avg_cycle_time_hours=140.0,
        median_cycle_time_hours=110.0,
        p90_cycle_time_hours=220.0,
        rework_cases=15,
        rework_percentage=0.15,
        sla_hours=720.0,
        sla_breach_cases=10,
        sla_breach_percentage=0.10,
        total_spend_usd=50000.0,
    )
    conformance = ConformanceOverviewResponse(
        dataset_id=overview.dataset_id,
        total_cases=100,
        conformant_cases=75,
        deviant_cases=25,
        conformance_percentage=75.0,  # FPY = 0.75 * (1 - 0.15) = 0.6375 < 0.80
        average_fitness_score=0.82,
        deviation_breakdown=[],
        active_rules=ConformanceRulesConfig(),
    )

    rec = evaluate_low_fpy(overview, 64, config)
    assert rec is not None
    assert rec.rule_id == "LOW_FPY"
    assert rec.category == "QUALITY"
    assert rec.actual_metric_value < 0.80


def test_evaluate_high_abandonment():
    config = RecommendationsConfig(high_abandonment_threshold=0.05)
    overview = OverviewMetrics(
        dataset_id=uuid.uuid4(),
        total_purchase_cases=100,
        total_events=600,
        completed_cases=88,
        incomplete_cases=12,  # 12% > 5%
        completion_rate=0.88,
        avg_cycle_time_hours=110.0,
        median_cycle_time_hours=95.0,
        p90_cycle_time_hours=180.0,
        rework_cases=3,
        rework_percentage=0.03,
        sla_hours=720.0,
        sla_breach_cases=2,
        sla_breach_percentage=0.02,
        total_spend_usd=35000.0,
    )

    rec = evaluate_high_abandonment(overview, config)
    assert rec is not None
    assert rec.rule_id == "HIGH_ABANDONMENT"
    assert rec.category == "EFFICIENCY"
    assert rec.affected_case_count == 12
    assert rec.affected_case_percentage == 12.0


def test_evaluate_sla_breach():
    config = RecommendationsConfig(sla_breach_threshold=0.10, sla_hours=720.0)
    overview = OverviewMetrics(
        dataset_id=uuid.uuid4(),
        total_purchase_cases=100,
        total_events=700,
        completed_cases=85,
        incomplete_cases=15,
        completion_rate=0.85,
        avg_cycle_time_hours=750.0,
        median_cycle_time_hours=600.0,
        p90_cycle_time_hours=920.0,
        rework_cases=5,
        rework_percentage=0.05,
        sla_hours=720.0,
        sla_breach_cases=22,  # 22% > 10%
        sla_breach_percentage=0.22,
        total_spend_usd=90000.0,
    )

    rec = evaluate_sla_breach(overview, config)
    assert rec is not None
    assert rec.rule_id == "SLA_BREACH"
    assert rec.category == "COMPLIANCE"
    assert rec.severity == "HIGH"  # > 20%
    assert rec.affected_case_count == 22


# ── 2. Integration Tests with Live Database Fixture ───────────────────────────

@pytest.fixture()
def seeded_recommendations_dataset(db: Session) -> Dataset:
    """
    Creates a deterministic dataset designed to trigger specific recommendation rules:
    - Case 1: Skipped Manager Approval (PO directly after PR)
    - Case 2: Early Invoice Verification (Invoice Verified before Goods Received)
    - Case 3: Rework loop (Manager Approval repeated twice)
    - Case 4: Long waiting delay on Manager Approval (30 hours)
    - Case 5: Abandoned case (terminated at Purchase Order Created)
    """
    ds = Dataset(
        id=uuid.uuid4(),
        name="Recommendation Test Event Log",
        filename="rec_test.csv",
        file_path="rec_test.csv",
        status="processed",
    )
    db.add(ds)
    db.commit()

    base_time = datetime(2025, 1, 1, 9, 0, 0, tzinfo=timezone.utc)

    events = [
        # Case 1: Skipped Approval (PR -> PO Created -> Goods Received -> Invoice Received -> Invoice Verified -> Payment Completed)
        CleanedEvent(dataset_id=ds.id, case_id="C-1", activity="Purchase Requisition", timestamp=datetime(2025, 1, 1, 9, 0, tzinfo=timezone.utc), extra_attributes={"amount": 1000.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-1", activity="Purchase Order Created", timestamp=datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc), extra_attributes={"amount": 1000.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-1", activity="Goods Received", timestamp=datetime(2025, 1, 1, 14, 0, tzinfo=timezone.utc), extra_attributes={"amount": 1000.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-1", activity="Invoice Received", timestamp=datetime(2025, 1, 1, 15, 0, tzinfo=timezone.utc), extra_attributes={"amount": 1000.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-1", activity="Invoice Verified", timestamp=datetime(2025, 1, 1, 16, 0, tzinfo=timezone.utc), extra_attributes={"amount": 1000.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-1", activity="Payment Completed", timestamp=datetime(2025, 1, 1, 18, 0, tzinfo=timezone.utc), extra_attributes={"amount": 1000.0}),

        # Case 2: Early Invoice Verification (Invoice Verified at 12:00, Goods Received at 16:00)
        CleanedEvent(dataset_id=ds.id, case_id="C-2", activity="Purchase Requisition", timestamp=datetime(2025, 1, 2, 9, 0, tzinfo=timezone.utc), extra_attributes={"amount": 2500.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-2", activity="Manager Approval", timestamp=datetime(2025, 1, 2, 10, 0, tzinfo=timezone.utc), extra_attributes={"amount": 2500.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-2", activity="Purchase Order Created", timestamp=datetime(2025, 1, 2, 11, 0, tzinfo=timezone.utc), extra_attributes={"amount": 2500.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-2", activity="Invoice Verified", timestamp=datetime(2025, 1, 2, 12, 0, tzinfo=timezone.utc), extra_attributes={"amount": 2500.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-2", activity="Goods Received", timestamp=datetime(2025, 1, 2, 16, 0, tzinfo=timezone.utc), extra_attributes={"amount": 2500.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-2", activity="Payment Completed", timestamp=datetime(2025, 1, 2, 18, 0, tzinfo=timezone.utc), extra_attributes={"amount": 2500.0}),

        # Case 3: Rework on Manager Approval (repeated twice)
        CleanedEvent(dataset_id=ds.id, case_id="C-3", activity="Purchase Requisition", timestamp=datetime(2025, 1, 3, 9, 0, tzinfo=timezone.utc), extra_attributes={"amount": 1800.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-3", activity="Manager Approval", timestamp=datetime(2025, 1, 3, 11, 0, tzinfo=timezone.utc), extra_attributes={"amount": 1800.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-3", activity="Manager Approval", timestamp=datetime(2025, 1, 3, 15, 0, tzinfo=timezone.utc), extra_attributes={"amount": 1800.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-3", activity="Purchase Order Created", timestamp=datetime(2025, 1, 3, 16, 0, tzinfo=timezone.utc), extra_attributes={"amount": 1800.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-3", activity="Goods Received", timestamp=datetime(2025, 1, 3, 17, 0, tzinfo=timezone.utc), extra_attributes={"amount": 1800.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-3", activity="Payment Completed", timestamp=datetime(2025, 1, 3, 18, 0, tzinfo=timezone.utc), extra_attributes={"amount": 1800.0}),

        # Case 4: Long waiting delay on Approval (PR at 9:00, Approval 30 hours later)
        CleanedEvent(dataset_id=ds.id, case_id="C-4", activity="Purchase Requisition", timestamp=datetime(2025, 1, 4, 9, 0, tzinfo=timezone.utc), extra_attributes={"amount": 3200.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-4", activity="Manager Approval", timestamp=datetime(2025, 1, 5, 15, 0, tzinfo=timezone.utc), extra_attributes={"amount": 3200.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-4", activity="Purchase Order Created", timestamp=datetime(2025, 1, 5, 16, 0, tzinfo=timezone.utc), extra_attributes={"amount": 3200.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-4", activity="Goods Received", timestamp=datetime(2025, 1, 5, 16, 15, tzinfo=timezone.utc), extra_attributes={"amount": 3200.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-4", activity="Invoice Received", timestamp=datetime(2025, 1, 5, 16, 30, tzinfo=timezone.utc), extra_attributes={"amount": 3200.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-4", activity="Invoice Verified", timestamp=datetime(2025, 1, 5, 17, 0, tzinfo=timezone.utc), extra_attributes={"amount": 3200.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-4", activity="Payment Completed", timestamp=datetime(2025, 1, 5, 18, 0, tzinfo=timezone.utc), extra_attributes={"amount": 3200.0}),

        # Case 5: Abandoned (incomplete, stopped at PO Created)
        CleanedEvent(dataset_id=ds.id, case_id="C-5", activity="Purchase Requisition", timestamp=datetime(2025, 1, 6, 9, 0, tzinfo=timezone.utc), extra_attributes={"amount": 500.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-5", activity="Manager Approval", timestamp=datetime(2025, 1, 6, 10, 0, tzinfo=timezone.utc), extra_attributes={"amount": 500.0}),
        CleanedEvent(dataset_id=ds.id, case_id="C-5", activity="Purchase Order Created", timestamp=datetime(2025, 1, 6, 12, 0, tzinfo=timezone.utc), extra_attributes={"amount": 500.0}),
    ]

    for event_id, event in enumerate(events, start=1):
        event.id = event_id

    db.add_all(events)
    db.commit()
    return ds


def test_generate_recommendations_integration(db: Session, seeded_recommendations_dataset: Dataset):
    """Verifies end-to-end recommendation generation from live database data."""
    config = RecommendationsConfig(
        skip_approval_threshold=0.0,
        early_invoice_threshold=0.0,
        high_rework_threshold=0.05,
        approval_bottleneck_hours=5.0,  # Approval wait on C-4 raises the average above this.
        high_abandonment_threshold=0.10,  # 1/5 = 20% abandonment triggers this
    )

    response = generate_recommendations(
        db=db,
        dataset_id=seeded_recommendations_dataset.id,
        config=config,
    )

    assert response.dataset_id == seeded_recommendations_dataset.id
    assert response.total_cases_analyzed == 5
    assert response.rules_evaluated_count == 8
    assert response.recommendations_count > 0

    rule_ids = {r.rule_id for r in response.recommendations}
    assert "SKIP_APPROVAL" in rule_ids
    assert "EARLY_INVOICE" in rule_ids
    assert "HIGH_REWORK" in rule_ids
    assert "HIGH_ABANDONMENT" in rule_ids
    low_fpy = next(r for r in response.recommendations if r.rule_id == "LOW_FPY")
    assert low_fpy.actual_metric_value == 0.2
    assert low_fpy.affected_case_count == 4
    bottleneck = next(r for r in response.recommendations if r.rule_id == "APPROVAL_BOTTLENECK")
    assert bottleneck.affected_case_count == 4

    # Recommendations must be sorted descending by estimated_impact_score
    scores = [r.estimated_impact_score for r in response.recommendations]
    assert scores == sorted(scores, reverse=True)

    # Every recommendation must have all required fields populated with non-zero metrics
    for r in response.recommendations:
        assert r.recommendation_id.startswith("REC-")
        assert len(r.business_problem) > 10
        assert len(r.recommended_corrective_action) > 15
        assert len(r.evidence_and_explanation) > 15
        assert r.affected_case_count > 0
        assert r.actual_metric_value > 0
        assert r.threshold_or_baseline
        assert r.supporting_metric
        assert r.estimated_operational_impact


def test_recommendations_api_endpoint(client: TestClient, seeded_recommendations_dataset: Dataset):
    """Verifies HTTP GET /api/v1/ai/recommendations endpoint."""
    res = client.get(f"/api/v1/ai/recommendations?dataset_id={seeded_recommendations_dataset.id}")
    assert res.status_code == 200
    data = res.json()
    assert data["total_cases_analyzed"] == 5
    assert data["recommendations_count"] > 0
    assert len(data["recommendations"]) == data["recommendations_count"]

    # Verify root /api alias works too
    res_alias = client.get(f"/api/ai/recommendations?dataset_id={seeded_recommendations_dataset.id}")
    assert res_alias.status_code == 200
    assert res_alias.json()["total_cases_analyzed"] == 5
