"""
Export & Reporting API Endpoints.

Provides three download formats derived from real computed data:
  - GET /reports/kpi-pdf          → PDF report (ReportLab) with overview + conformance KPIs
  - GET /reports/events-csv       → Streaming CSV of cleaned events for the dataset
  - GET /reports/conformance-json → Full JSON conformance report download
"""
from __future__ import annotations

import csv
import io
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional
from xml.sax.saxutils import escape

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session

from app.analytics.service import (
    get_bottleneck_analytics,
    get_cycle_time_analytics,
    get_overview_analytics,
)
from app.conformance.engine import get_conformance_overview_response
from app.db.session import get_db
from app.models.dataset import CleanedEvent, Dataset
from app.schemas.analytics import BottlenecksResponse, CycleTimeMetrics, OverviewMetrics
from app.schemas.conformance import ConformanceOverviewResponse

router = APIRouter(prefix="/reports", tags=["Export & Reporting"])


# ── Helper: verify dataset exists ─────────────────────────────────────────────

def _require_dataset(db: Session, dataset_id: uuid.UUID) -> Dataset:
    ds = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not ds:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found.",
        )
    return ds


def _validate_date_range(
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> None:
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date must be earlier than or equal to end_date.",
        )


def _safe_filename_part(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")[:40] or "dataset"


def _collect_report_metrics(
    db: Session,
    dataset_id: uuid.UUID,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    sla_hours: float,
) -> tuple[
    OverviewMetrics,
    CycleTimeMetrics,
    BottlenecksResponse,
    ConformanceOverviewResponse,
]:
    bottleneck_metrics = get_bottleneck_analytics(
        db, dataset_id, start_date=start_date, end_date=end_date
    )
    top_bottlenecks = bottleneck_metrics.model_copy(
        update={"bottlenecks": bottleneck_metrics.bottlenecks[:5]}
    )
    return (
        get_overview_analytics(
            db, dataset_id, start_date=start_date, end_date=end_date, sla_hours=sla_hours
        ),
        get_cycle_time_analytics(
            db, dataset_id, start_date=start_date, end_date=end_date, sla_hours=sla_hours
        ),
        top_bottlenecks,
        get_conformance_overview_response(
            db, dataset_id, start_date=start_date, end_date=end_date
        ),
    )


# ── 1. KPI PDF Report ─────────────────────────────────────────────────────────

@router.get(
    "/kpi-pdf",
    summary="Download KPI summary PDF",
    description=(
        "Generates a professional PDF report containing operational overview KPIs, "
        "cycle time statistics, top bottlenecks, and conformance summary. "
        "All values are derived from real database computations."
    ),
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "PDF report file",
        }
    },
)
def download_kpi_pdf(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    sla_hours: float = Query(720.0, ge=1.0, description="SLA threshold in hours"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
) -> Response:
    ds = _require_dataset(db, dataset_id)
    _validate_date_range(start_date, end_date)
    generated_at = datetime.now(timezone.utc)

    overview, cycle, bottlenecks, conformance = _collect_report_metrics(
        db, dataset_id, start_date, end_date, sla_hours
    )

    pdf_bytes = _build_kpi_pdf(
        ds,
        overview,
        cycle,
        bottlenecks,
        conformance,
        sla_hours,
        start_date,
        end_date,
        generated_at,
    )

    safe_name = _safe_filename_part(ds.name)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="flowmind_kpi_{safe_name}.pdf"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )


def _build_kpi_pdf(
    ds: Dataset,
    overview: OverviewMetrics,
    cycle: CycleTimeMetrics,
    bottlenecks: BottlenecksResponse,
    conformance: ConformanceOverviewResponse,
    sla_hours: float,
    start_date: Optional[datetime],
    end_date: Optional[datetime],
    generated_at: datetime,
) -> bytes:
    """Builds the PDF bytes using ReportLab Platypus."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    # Colour palette — matches FlowMind dark navy theme
    NAVY = colors.HexColor("#0f172a")
    SLATE = colors.HexColor("#1e293b")
    BLUE = colors.HexColor("#3b82f6")
    LIGHT = colors.HexColor("#f8fafc")
    GRAY = colors.HexColor("#64748b")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], textColor=NAVY, fontSize=20, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=styles["Heading2"], textColor=SLATE, fontSize=13, spaceBefore=16, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=styles["Normal"], fontSize=8, textColor=GRAY)

    def rule(c=BLUE):
        return HRFlowable(width="100%", thickness=1, color=c, spaceAfter=6)

    def kv_table(rows, col_w=None):
        col_w = col_w or [9 * cm, 7 * cm]
        t = Table(rows, colWidths=col_w)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT, colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.4, GRAY),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        return t

    generated_label = generated_at.strftime("%Y-%m-%d %H:%M UTC")
    date_range = "All time"
    if start_date or end_date:
        s = start_date.isoformat() if start_date else "Not set"
        e = end_date.isoformat() if end_date else "Not set"
        date_range = f"{s} → {e}"

    story = [
        Paragraph("FlowMind Process Mining", h1),
        Paragraph(f"<b>KPI Summary Report</b> — {escape(ds.name)}", h2),
        Paragraph(
            f"Generated: {generated_label} &nbsp;|&nbsp; SLA threshold: "
            f"{sla_hours:,.0f} h &nbsp;|&nbsp; Period: {date_range}",
            sub,
        ),
        Spacer(1, 0.3 * cm),
        rule(),

        Paragraph("Dataset and Selected Filters", h2),
        kv_table([
            ["Field", "Value"],
            ["Dataset ID", str(ds.id)],
            ["Source file", ds.filename],
            ["Dataset status", ds.status],
            ["Source rows", f"{ds.total_rows_raw:,}"],
            ["Start date (inclusive)", start_date.isoformat() if start_date else "Not set"],
            ["End date (inclusive)", end_date.isoformat() if end_date else "Not set"],
        ]),
        Spacer(1, 0.4 * cm),

        # ── Overview KPIs ───────────────────────────────────────────────────
        Paragraph("1. Operational Overview", h2),
        kv_table([
            ["Metric", "Value"],
            ["Total Purchase Cases", f"{overview.total_purchase_cases:,}"],
            ["Total Events", f"{overview.total_events:,}"],
            ["Completed Cases", f"{overview.completed_cases:,}"],
            ["Incomplete Cases", f"{overview.incomplete_cases:,}"],
            ["Completion Rate", f"{overview.completion_rate:.1f}%"],
            ["Rework Cases", f"{overview.rework_cases:,}"],
            ["Rework Percentage", f"{overview.rework_percentage:.2f}%"],
            ["SLA Breach Cases", f"{overview.sla_breach_cases:,}"],
            ["SLA Breach Rate", f"{overview.sla_breach_percentage:.2f}%"],
            ["Total Spend (USD)", f"${overview.total_spend_usd:,.2f}"],
        ]),
        Spacer(1, 0.4 * cm),

        # ── Cycle Time ──────────────────────────────────────────────────────
        Paragraph("2. Cycle Time Statistics", h2),
        kv_table([
            ["Metric", "Value"],
            ["Avg Cycle Time", f"{cycle.avg_cycle_time_hours:.1f} h"],
            ["Median Cycle Time", f"{cycle.median_cycle_time_hours:.1f} h"],
            ["P75 Cycle Time", f"{cycle.p75_cycle_time_hours:.1f} h"],
            ["P90 Cycle Time", f"{cycle.p90_cycle_time_hours:.1f} h"],
            ["P95 Cycle Time", f"{cycle.p95_cycle_time_hours:.1f} h"],
            ["Min Cycle Time", f"{cycle.min_cycle_time_hours:.1f} h"],
            ["Max Cycle Time", f"{cycle.max_cycle_time_hours:.1f} h"],
            ["SLA Breach Count", f"{cycle.sla_breach_count:,}"],
            ["SLA Breach Rate", f"{cycle.sla_breach_percentage:.2f}%"],
        ]),
        Spacer(1, 0.4 * cm),

        # ── Conformance ─────────────────────────────────────────────────────
        Paragraph("3. Conformance Summary", h2),
        kv_table([
            ["Metric", "Value"],
            ["Total Cases", f"{conformance.total_cases:,}"],
            ["Conformant Cases", f"{conformance.conformant_cases:,}"],
            ["Deviant Cases", f"{conformance.deviant_cases:,}"],
            ["Conformance Rate", f"{conformance.conformance_percentage:.2f}%"],
            ["Avg Fitness Score", f"{conformance.average_fitness_score:.4f}"],
        ]),
        Spacer(1, 0.3 * cm),
    ]

    # Deviation breakdown table
    if conformance.deviation_breakdown:
        dev_rows = [["Deviation Type", "Category", "Severity", "Cases", "%"]]
        for d in conformance.deviation_breakdown:
            dev_rows.append([
                d.deviation_type,
                d.category,
                d.severity,
                f"{d.affected_cases:,}",
                f"{d.percentage_of_cases:.2f}%",
            ])
        t = Table(dev_rows, colWidths=[5.5 * cm, 3 * cm, 2.5 * cm, 2 * cm, 2 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT, colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.4, GRAY),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4 * cm))

    # ── Top Bottlenecks ──────────────────────────────────────────────────────
    if bottlenecks.bottlenecks:
        story.append(Paragraph("4. Top Process Bottlenecks", h2))
        btn_rows = [["Rank", "Activity", "Score", "Avg Wait (h)", "SLA Breach %"]]
        for b in bottlenecks.bottlenecks:
            btn_rows.append([
                str(b.rank),
                b.activity,
                f"{b.bottleneck_score:.2f}",
                f"{b.avg_waiting_time_hours:.1f}",
                f"{b.sla_breach_rate * 100:.1f}%",
            ])
        t = Table(btn_rows, colWidths=[1.5 * cm, 7 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT, colors.white]),
            ("GRID", (0, 0), (-1, -1), 0.4, GRAY),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.4 * cm))

    # ── Footer note ──────────────────────────────────────────────────────────
    story.append(rule(GRAY))
    story.append(
        Paragraph(
            "All values in this report are derived from actual database records. "
            "No values have been fabricated or estimated. "
            "Generated by FlowMind Process Mining Platform.",
            sub,
        )
    )

    doc.build(story)
    return buf.getvalue()


# ── 2. Events CSV Export ──────────────────────────────────────────────────────

@router.get(
    "/events-csv",
    summary="Download filtered cleaned events as CSV",
    description=(
        "Streams CleanedEvent rows within the selected inclusive date range. The CSV "
        "includes dataset/filter metadata followed by case_id, activity, timestamp, "
        "and event attributes."
    ),
    responses={
        200: {
            "content": {"text/csv": {}},
            "description": "CSV file of cleaned events",
        }
    },
)
def download_events_csv(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None, description="Inclusive start timestamp"),
    end_date: Optional[datetime] = Query(None, description="Inclusive end timestamp"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    ds = _require_dataset(db, dataset_id)
    _validate_date_range(start_date, end_date)
    generated_at = datetime.now(timezone.utc)

    def _generate():
        buf = io.StringIO(newline="")
        writer = csv.writer(buf)
        writer.writerow(["# FlowMind filtered event-log export"])
        writer.writerow([f"# Dataset ID: {ds.id}"])
        writer.writerow([f"# Dataset name: {ds.name}"])
        writer.writerow([f"# Source file: {ds.filename}"])
        writer.writerow([f"# Dataset status: {ds.status}"])
        writer.writerow([f"# Generated at UTC: {generated_at.isoformat()}"])
        writer.writerow([
            f"# Start date (inclusive): {start_date.isoformat() if start_date else 'Not set'}"
        ])
        writer.writerow([
            f"# End date (inclusive): {end_date.isoformat() if end_date else 'Not set'}"
        ])
        writer.writerow([
            "case_id", "activity", "timestamp", "event_id",
            "vendor_id", "department", "amount_usd", "extra_attributes",
        ])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        query = db.query(CleanedEvent).filter(CleanedEvent.dataset_id == dataset_id)
        if start_date:
            query = query.filter(CleanedEvent.timestamp >= start_date)
        if end_date:
            query = query.filter(CleanedEvent.timestamp <= end_date)
        events = query.order_by(
            CleanedEvent.case_id,
            CleanedEvent.timestamp,
            CleanedEvent.id,
        ).yield_per(2000)

        rows_in_chunk = 0
        for ev in events:
            extra = ev.extra_attributes or {}
            writer.writerow([
                ev.case_id,
                ev.activity,
                ev.timestamp.isoformat() if ev.timestamp else "",
                ev.id,
                extra.get("vendor_id", ""),
                extra.get("department", ""),
                extra.get("amount", ""),
                json.dumps({
                    k: v
                    for k, v in extra.items()
                    if k not in ("vendor_id", "department", "amount")
                }),
            ])
            rows_in_chunk += 1
            if rows_in_chunk == 2000:
                yield buf.getvalue()
                buf.seek(0)
                buf.truncate(0)
                rows_in_chunk = 0

        if rows_in_chunk:
            yield buf.getvalue()

    safe_name = _safe_filename_part(ds.name)
    return StreamingResponse(
        _generate(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="flowmind_events_{safe_name}.csv"',
        },
    )


# ── 3. Conformance JSON Export ────────────────────────────────────────────────

@router.get(
    "/conformance-json",
    summary="Download KPI and conformance audit report as JSON",
    description=(
        "Downloads dataset and filter metadata, overview and cycle-time KPIs, top "
        "bottlenecks, conformance metrics, active rules, and deviation breakdown."
    ),
    responses={
        200: {
            "content": {"application/json": {}},
            "description": "Full conformance report JSON",
        }
    },
)
def download_conformance_json(
    dataset_id: uuid.UUID = Query(..., description="Target dataset UUID"),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
) -> Response:
    ds = _require_dataset(db, dataset_id)
    _validate_date_range(start_date, end_date)
    generated_at = datetime.now(timezone.utc)

    overview, cycle, bottlenecks, conformance = _collect_report_metrics(
        db, dataset_id, start_date, end_date, sla_hours=720.0
    )

    report = {
        "report_type": "conformance_audit",
        "generated_at": generated_at.isoformat(),
        "platform": "FlowMind Process Mining",
        "note": "All values derived from actual database computations.",
        "dataset": {
            "id": str(ds.id),
            "name": ds.name,
            "filename": ds.filename,
            "status": ds.status,
            "source_rows": ds.total_rows_raw,
            "created_at": ds.created_at.isoformat() if ds.created_at else None,
        },
        "filters": {
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat() if end_date else None,
            "sla_hours": 720.0,
        },
        "kpis": {
            "overview": overview.model_dump(mode="json"),
            "cycle_time": cycle.model_dump(mode="json"),
        },
        "bottlenecks": bottlenecks.model_dump(mode="json"),
        "conformance_report": conformance.model_dump(mode="json"),
    }
    payload = json.dumps(report, indent=2, default=str).encode("utf-8")

    return Response(
        content=payload,
        media_type="application/json",
        headers={
            "Content-Disposition": (
                f'attachment; filename="flowmind_conformance_{_safe_filename_part(ds.name)}.json"'
            ),
            "Content-Length": str(len(payload)),
        },
    )
