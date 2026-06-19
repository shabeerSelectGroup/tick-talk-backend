"""PDF event summary export."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.event import Event


def generate_pdf_summary(event: Event, context: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=22,
        textColor=colors.HexColor("#0d9488"),
        spaceAfter=12,
    )
    story = []

    ev = context["event"]
    summary = context["summary"]
    story.append(Paragraph("Tick Talk — Event Summary", styles["Normal"]))
    story.append(Paragraph(ev["name"], title_style))
    story.append(Paragraph(f"Code: {ev['code']} · Mode: {ev['mode']} · Status: {ev['status']}", styles["Normal"]))
    story.append(Spacer(1, 0.2 * inch))

    if ev.get("starts_at") or ev.get("ends_at"):
        story.append(
            Paragraph(
                f"Schedule: {ev.get('starts_at', '—')} → {ev.get('ends_at', '—')}",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 0.15 * inch))

    metrics: list[list[str]] = []
    mode = summary.get("mode", ev["mode"])
    if mode == "networking":
        metrics = [
            ["Active participants", str(summary.get("participants_active", 0))],
            ["Total connections", str(summary.get("total_connections", 0))],
            ["Tasks completed", str(summary.get("tasks_completed", 0))],
            ["Selfies uploaded", str(summary.get("selfies_uploaded", 0))],
            ["Avg connections / person", str(summary.get("avg_connections_per_participant", 0))],
            ["Connection rate", str(summary.get("connection_rate", 0))],
        ]
    else:
        metrics = [
            ["Participants", str(summary.get("participant_count", 0))],
            ["Total scans / matches", str(summary.get("total_matches", 0))],
            ["Tasks completed", str(summary.get("total_tasks_completed", 0))],
            ["Selfies uploaded", str(summary.get("selfies_uploaded", 0))],
        ]

    t = Table([["Metric", "Value"], *metrics], colWidths=[3.5 * inch, 2 * inch])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#115e59")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0fdfa")]),
            ]
        )
    )
    story.append(t)
    story.append(Spacer(1, 0.25 * inch))

    top_tasks = summary.get("top_tasks") or []
    if top_tasks:
        story.append(Paragraph("Top completed tasks", styles["Heading2"]))
        rows = [["Task", "Completions"]] + [
            [str(t.get("title", "")), str(t.get("completions", 0))] for t in top_tasks[:10]
        ]
        tt = Table(rows, colWidths=[4 * inch, 1.5 * inch])
        tt.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
        story.append(tt)
        story.append(Spacer(1, 0.2 * inch))

    board = summary.get("leaderboard_top") or []
    if board:
        story.append(Paragraph("Leaderboard (top 10)", styles["Heading2"]))
        rows = [["Rank", "Name", "Score", "Tasks"]] + [
            [
                str(r.get("rank", "")),
                str(r.get("display_name", "")),
                str(r.get("score", 0)),
                str(r.get("tasks_completed", 0)),
            ]
            for r in board[:10]
        ]
        lb = Table(rows, colWidths=[0.6 * inch, 2.5 * inch, 1 * inch, 1 * inch])
        lb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))
        story.append(lb)

    doc.build(story)
    return buffer.getvalue()
