"""Seed admin and optional demo event. Run: python -m scripts.seed"""

import asyncio
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import async_session_factory
from app.models.admin import Admin
from app.models.enums import AdminRole
from app.models.enums import EventMode, EventStatus, TaskType
from app.models.event import Event
from app.models.event_settings import EventSettings
from app.models.task import Task

from app.data.networking_bingo_tasks import networking_bingo_task_templates


async def main() -> None:
    async with async_session_factory() as db:
        if not await db.scalar(select(Admin).where(Admin.email == "admin@ticktalk.app")):
            db.add(
                Admin(
                    email="admin@ticktalk.app",
                    password_hash=hash_password("changeme"),
                    name="Tick Talk Super Admin",
                    role=AdminRole.SUPER_ADMIN,
                )
            )
        if not await db.scalar(select(Event).where(Event.code == "DEMO2026")):
            now = datetime.now(timezone.utc)
            event = Event(
                code="DEMO2026",
                name="Demo Networking Event",
                description="Connect, complete shared tasks, and verify with selfies",
                mode=EventMode.NETWORKING,
                status=EventStatus.LIVE,
                starts_at=now,
                ends_at=now + timedelta(hours=2),
            )
            db.add(event)
            await db.flush()
            db.add(
                EventSettings(
                    event_id=event.id,
                    duration_minutes=120,
                    leaderboard_enabled=False,
                    enable_public_wall=True,
                    enable_selfie_verification=True,
                    scan_match_points=0,
                    selfie_requires_approval=True,
                )
            )
            for order, tmpl in enumerate(networking_bingo_task_templates()):
                db.add(
                    Task(
                        event_id=event.id,
                        slug=tmpl["slug"],
                        title=tmpl["title"],
                        description=tmpl["description"],
                        type=tmpl["type"],
                        points=0,
                        sort_order=order,
                        config_json=tmpl.get("config_json"),
                    )
                )

        if not await db.scalar(select(Event).where(Event.code == "COMP2026")):
            now = datetime.now(timezone.utc)
            comp = Event(
                code="COMP2026",
                name="Demo Competition Event",
                description="Competition mode with leaderboard and scores",
                mode=EventMode.COMPETITION,
                status=EventStatus.SCHEDULED,
                starts_at=now,
                ends_at=now + timedelta(hours=3),
            )
            db.add(comp)
            await db.flush()
            db.add(
                EventSettings(
                    event_id=comp.id,
                    duration_minutes=180,
                    leaderboard_enabled=True,
                    leaderboard_size=20,
                    scan_match_points=10,
                )
            )

        await db.commit()
    print("Seed complete:")
    print("  Admin login: ADMIN_SECURITY_CODE from .env (account: admin@ticktalk.app)")
    print("  Demo event code: DEMO2026")


if __name__ == "__main__":
    asyncio.run(main())
