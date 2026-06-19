from app.schemas.task import BulkImportRequest, normalize_title
from app.services.tasks import parse_bulk_text, slugify


def test_normalize_title_duplicate_detection():
    assert normalize_title("Find  someone  in HR") == normalize_title("find someone in hr")


def test_slugify():
    slug = slugify("Find someone who works in HR")
    assert "-" in slug
    assert len(slug) <= 64


def test_parse_bulk_text():
    text = """# comment
Find someone who works in HR
Find someone who speaks 3 languages|Must speak 3+ languages
"""
    lines = parse_bulk_text(text)
    assert len(lines) == 2
    assert lines[1].description == "Must speak 3+ languages"


def test_bulk_import_request_requires_content():
    req = BulkImportRequest(text="One task title here")
    assert req.text is not None
