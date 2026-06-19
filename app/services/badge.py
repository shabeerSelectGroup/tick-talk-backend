"""Participant QR badge: signed payload, validation, and asset generation."""

from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.models.event import Event
from app.models.participant import Participant
from app.services.qr import generate_qr_data_url, generate_qr_png_bytes
from app.services.session import generate_token

BADGE_SCHEME = "ticktalk://badge"
BADGE_VERSION = "v1"
LEGACY_PATTERN = re.compile(r"^ticktalk://badge/(?P<token>[A-Za-z0-9_-]+)$")
V1_PATTERN = re.compile(
    r"^ticktalk://badge/v1/(?P<event_id>\d+)/(?P<participant_id>\d+)/(?P<token>[A-Za-z0-9_-]+)/(?P<sig>[a-f0-9]{16})$"
)


class BadgeError(AppError):
    pass


@dataclass(frozen=True)
class BadgeClaims:
    event_id: int
    participant_id: int
    token: str
    signature: str


@dataclass(frozen=True)
class BadgeData:
    participant_id: int
    event_id: int
    event_code: str
    display_name: str
    secure_token: str
    qr_payload: str
    qr_code_data_url: str
    version: str = BADGE_VERSION


@dataclass(frozen=True)
class BadgeValidationResult:
    valid: bool
    participant_id: int | None = None
    event_id: int | None = None
    display_name: str | None = None
    company: str | None = None
    error_code: str | None = None
    message: str | None = None


def generate_secure_badge_token() -> str:
    """Opaque per-participant token stored in DB (`participants.qr_code`)."""
    return generate_token()


def _signing_message(event_id: int, participant_id: int, token: str) -> str:
    return f"{BADGE_VERSION}:{event_id}:{participant_id}:{token}"


def sign_badge(event_id: int, participant_id: int, token: str) -> str:
    """HMAC-SHA256 truncated to 16 hex chars — prevents ID/token tampering."""
    settings = get_settings()
    digest = hmac.new(
        settings.app_secret_key.encode(),
        _signing_message(event_id, participant_id, token).encode(),
        hashlib.sha256,
    ).hexdigest()
    return digest[:16]


def verify_badge_signature(event_id: int, participant_id: int, token: str, signature: str) -> bool:
    if not signature or len(signature) != 16:
        return False
    expected = sign_badge(event_id, participant_id, token)
    return hmac.compare_digest(expected, signature.lower())


def build_badge_payload(event_id: int, participant_id: int, token: str) -> str:
    sig = sign_badge(event_id, participant_id, token)
    return f"{BADGE_SCHEME}/{BADGE_VERSION}/{event_id}/{participant_id}/{token}/{sig}"


def build_badge_data(participant: Participant, event: Event) -> BadgeData:
    payload = build_badge_payload(participant.event_id, participant.id, participant.qr_code)
    return BadgeData(
        participant_id=participant.id,
        event_id=participant.event_id,
        event_code=event.code,
        display_name=participant.display_name,
        secure_token=participant.qr_code,
        qr_payload=payload,
        qr_code_data_url=generate_qr_data_url(payload),
    )


def parse_badge_input(raw: str) -> BadgeClaims | str | None:
    """
    Parse QR text. Returns BadgeClaims (v1), legacy token string, or None.
    """
    text = raw.strip()
    if not text:
        return None

    v1 = V1_PATTERN.match(text)
    if v1:
        return BadgeClaims(
            event_id=int(v1.group("event_id")),
            participant_id=int(v1.group("participant_id")),
            token=v1.group("token"),
            signature=v1.group("sig"),
        )

    legacy = LEGACY_PATTERN.match(text)
    if legacy:
        return legacy.group("token")

    # Bare token fallback (manual paste)
    if re.fullmatch(r"[A-Za-z0-9_-]{16,64}", text):
        return text

    # Legacy path suffix only
    if "ticktalk://badge/" in text and "/v1/" not in text:
        token = text.rsplit("/", 1)[-1].strip()
        return token if token else None

    return None


async def resolve_participant_from_badge(
    db: AsyncSession,
    raw: str,
    *,
    scanner_event_id: int | None = None,
    require_signature: bool = True,
) -> Participant:
    """Resolve and cryptographically validate a scanned badge."""
    parsed = parse_badge_input(raw)
    if parsed is None:
        raise BadgeError("BADGE_INVALID", "Unrecognized QR badge format.", 400)

    if isinstance(parsed, BadgeClaims):
        if require_signature and not verify_badge_signature(
            parsed.event_id, parsed.participant_id, parsed.token, parsed.signature
        ):
            raise BadgeError("BADGE_SIGNATURE_INVALID", "Badge signature is invalid or tampered.", 403)

        result = await db.execute(
            select(Participant).where(
                Participant.id == parsed.participant_id,
                Participant.event_id == parsed.event_id,
                Participant.qr_code == parsed.token,
                Participant.is_active.is_(True),
            )
        )
        participant = result.scalar_one_or_none()
        if not participant:
            raise BadgeError("BADGE_NOT_FOUND", "Badge does not match any active participant.", 404)

        if scanner_event_id is not None and participant.event_id != scanner_event_id:
            raise BadgeError(
                "BADGE_WRONG_EVENT",
                "This badge belongs to a different event.",
                403,
            )
        return participant

    # Legacy: lookup by token only
    result = await db.execute(
        select(Participant).where(
            Participant.qr_code == parsed,
            Participant.is_active.is_(True),
        )
    )
    participant = result.scalar_one_or_none()
    if not participant:
        raise BadgeError("BADGE_NOT_FOUND", "Invalid QR badge.", 404)

    if scanner_event_id is not None and participant.event_id != scanner_event_id:
        raise BadgeError(
            "BADGE_WRONG_EVENT",
            "This badge belongs to a different event.",
            403,
        )
    return participant


async def validate_badge_for_scanner(
    db: AsyncSession,
    raw: str,
    scanner: Participant,
) -> BadgeValidationResult:
    """Validate badge without recording a match (preview / UX)."""
    try:
        partner = await resolve_participant_from_badge(
            db, raw, scanner_event_id=scanner.event_id
        )
    except BadgeError as e:
        return BadgeValidationResult(
            valid=False,
            error_code=e.code,
            message=e.message,
        )

    if partner.id == scanner.id:
        return BadgeValidationResult(
            valid=False,
            error_code="BADGE_SELF_SCAN",
            message="You cannot scan your own badge.",
        )

    return BadgeValidationResult(
        valid=True,
        participant_id=partner.id,
        event_id=partner.event_id,
        display_name=partner.display_name,
        company=partner.company,
        message="Valid badge",
    )
