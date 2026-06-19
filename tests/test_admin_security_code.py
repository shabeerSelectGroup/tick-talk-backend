import secrets

from app.core.config import Settings


def test_security_code_compare_digest():
    settings = Settings(admin_security_code="secret-code")
    expected = settings.admin_security_code.strip()
    assert secrets.compare_digest("secret-code", expected)
    assert not secrets.compare_digest("wrong", expected)
