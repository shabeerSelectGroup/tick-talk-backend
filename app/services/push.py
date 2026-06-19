"""Web Push (VAPID) — subscribe and send notifications."""

from __future__ import annotations

import json
import logging

from pywebpush import WebPushException, webpush
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.push_subscription import PushSubscription

logger = logging.getLogger(__name__)


def vapid_configured() -> bool:
    s = get_settings()
    return bool(s.vapid_public_key and s.vapid_private_key and s.vapid_subject)


def get_vapid_public_key() -> str | None:
    key = get_settings().vapid_public_key
    return key or None


async def upsert_subscription(
    db: AsyncSession,
    participant_id: int,
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
) -> PushSubscription:
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    row = result.scalar_one_or_none()
    if row:
        row.participant_id = participant_id
        row.p256dh = p256dh
        row.auth = auth
    else:
        row = PushSubscription(
            participant_id=participant_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
        )
        db.add(row)
    await db.flush()
    return row


async def remove_subscription(db: AsyncSession, endpoint: str) -> None:
    await db.execute(delete(PushSubscription).where(PushSubscription.endpoint == endpoint))


def send_push_sync(
    subscription: PushSubscription,
    *,
    title: str,
    body: str,
    url: str = "/",
) -> bool:
    if not vapid_configured():
        return False
    settings = get_settings()
    payload = json.dumps({"title": title, "body": body, "url": url})
    try:
        webpush(
            subscription_info={
                "endpoint": subscription.endpoint,
                "keys": {"p256dh": subscription.p256dh, "auth": subscription.auth},
            },
            data=payload,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
        )
        return True
    except WebPushException as e:
        logger.warning("Push failed for %s: %s", subscription.id, e)
        return False


async def notify_participant(
    db: AsyncSession,
    participant_id: int,
    *,
    title: str,
    body: str,
    url: str = "/home",
) -> int:
    if not vapid_configured():
        return 0
    result = await db.execute(
        select(PushSubscription).where(PushSubscription.participant_id == participant_id)
    )
    sent = 0
    for sub in result.scalars().all():
        if send_push_sync(sub, title=title, body=body, url=url):
            sent += 1
    return sent
