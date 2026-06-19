from app.core.config import get_settings
from app.services.badge import (
    BADGE_VERSION,
    BadgeClaims,
    build_badge_payload,
    parse_badge_input,
    sign_badge,
    verify_badge_signature,
)


def test_sign_and_verify_badge():
    sig = sign_badge(10, 42, "secure-token-abc")
    assert verify_badge_signature(10, 42, "secure-token-abc", sig)
    assert not verify_badge_signature(10, 42, "wrong-token", sig)
    assert not verify_badge_signature(11, 42, "secure-token-abc", sig)


def test_build_badge_payload_format():
    token = "a" * 32
    payload = build_badge_payload(5, 99, token)
    assert payload.startswith("ticktalk://badge/v1/5/99/")
    assert payload.endswith("/" + sign_badge(5, 99, token))


def test_parse_v1_payload():
    token = "testtoken123"
    payload = build_badge_payload(3, 7, token)
    parsed = parse_badge_input(payload)
    assert isinstance(parsed, BadgeClaims)
    assert parsed.event_id == 3
    assert parsed.participant_id == 7
    assert parsed.token == token


def test_parse_legacy_payload():
    parsed = parse_badge_input("ticktalk://badge/legacyOnlyToken")
    assert parsed == "legacyOnlyToken"


def test_tampered_signature_rejected():
    token = "tok"
    payload = build_badge_payload(1, 2, token)
    tampered = payload[:-1] + ("0" if payload[-1] != "0" else "1")
    claims = parse_badge_input(tampered)
    assert isinstance(claims, BadgeClaims)
    assert not verify_badge_signature(claims.event_id, claims.participant_id, claims.token, claims.signature)


def test_signature_uses_app_secret():
    get_settings.cache_clear()
    payload = build_badge_payload(1, 1, "x")
    sig = payload.rsplit("/", 1)[-1]
    assert len(sig) == 16
