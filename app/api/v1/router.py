from fastapi import APIRouter

from app.api.v1 import (
    admin_auth,
    admin_events,
    admin_reports,
    admin_tasks,
    media,
    participant,
    participant_tasks,
    wall,
    ws,
)

api_router = APIRouter()
api_router.include_router(admin_auth.router, prefix="/admin/auth", tags=["admin-auth"])
api_router.include_router(admin_events.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_reports.router, prefix="/admin", tags=["admin-reports"])
api_router.include_router(admin_tasks.router, prefix="/admin", tags=["admin-tasks"])
api_router.include_router(participant.router, prefix="/participant", tags=["participant"])
api_router.include_router(
    participant_tasks.router, prefix="/participant", tags=["participant-tasks"]
)
api_router.include_router(media.router, tags=["media"])
api_router.include_router(wall.router, prefix="/wall", tags=["wall"])
api_router.include_router(ws.router, tags=["websocket"])
