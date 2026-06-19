from app.models.enums import ExportType
from app.services.reports.excel_export import generate_excel_participants
from app.services.reports.jobs import export_type_label
from app.services.reports.pdf_export import generate_pdf_summary


class FakeEvent:
    code = "TEST"
    name = "Test Event"


def test_export_type_labels():
    assert "PDF" in export_type_label(ExportType.PDF_SUMMARY)
    assert "ZIP" in export_type_label(ExportType.ZIP_SELFIES)


def test_pdf_summary_bytes():
    event = FakeEvent()
    ctx = {
        "event": {
            "code": "TEST",
            "name": "Test",
            "mode": "networking",
            "status": "live",
            "starts_at": "",
            "ends_at": "",
        },
        "summary": {
            "mode": "networking",
            "participants_active": 10,
            "total_connections": 25,
            "tasks_completed": 5,
            "selfies_uploaded": 3,
            "avg_connections_per_participant": 2.5,
            "connection_rate": 2.5,
        },
    }
    data = generate_pdf_summary(event, ctx)
    assert data[:4] == b"%PDF"


def test_excel_participants_bytes():
    data = generate_excel_participants(
        [
            {
                "id": 1,
                "display_name": "Alice",
                "email": "a@test.com",
                "company": "Co",
                "title": "",
                "score": 0,
                "rank": "",
                "tasks_completed": 1,
                "matches_count": 2,
                "progress_percent": 50.0,
                "joined_at": "2026-01-01",
            }
        ]
    )
    assert data[:2] == b"PK"
