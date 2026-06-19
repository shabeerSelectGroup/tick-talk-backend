from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.enums import AdminRole


def test_password_hashing():
    hashed = hash_password("securepassword")
    assert hashed != "securepassword"
    assert verify_password("securepassword", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_contains_role():
    token = create_access_token("1", AdminRole.SUPER_ADMIN.value)
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "1"
    assert payload["type"] == "access"
    assert payload["role"] == "super_admin"
    assert "jti" in payload


def test_refresh_token_roundtrip():
    token, jti, expires = create_refresh_token("42")
    assert jti
    assert expires
    payload = decode_token(token)
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti
    assert hash_refresh_token(token) == hash_refresh_token(token)
