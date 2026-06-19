from app.services.participant_registration import parse_bulk_names


def test_parse_bulk_names_one_per_line():
    text = """
    Alex Kim
    Jordan Lee | jordan@test.com
    # comment
    Sam | sam@test.com | Acme
    """
    entries = parse_bulk_names(text)
    assert len(entries) == 3
    assert entries[0]["display_name"] == "Alex Kim"
    assert entries[0]["email"] is None
    assert entries[1]["email"] == "jordan@test.com"
    assert entries[2]["company"] == "Acme"


def test_parse_bulk_names_skips_short_lines():
    assert parse_bulk_names("A\nBob Smith") == [{"display_name": "Bob Smith", "email": None, "company": None}]
