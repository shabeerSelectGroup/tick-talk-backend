from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_participant
from app.core.exceptions import AppError
from app.db.session import get_db
from app.models.enums import ActivityType
from app.models.participant import Participant
from app.schemas.common import ok
from app.schemas.task_flow import (
    TaskFlowCompleteRequest,
    TaskFlowCompleteResponse,
    TaskFlowScanRequest,
    TaskFlowScanResponse,
    TaskFlowSelfieUploadResponse,
    TaskFlowStateResponse,
    TaskFlowValidateScanResponse,
)
from app.services.activity import log_activity
from app.services.ws_events import emit_selfie_uploaded, emit_task_completed
from app.services.selfie_storage import SelfieStorageError, SelfieUploadContext, upload_selfie
from app.services.manual_task import ManualTaskError, toggle_manual_participant_task
from app.services.task_completion import (
    TaskCompletionError,
    _flow_meta,
    assert_flow_ready_for_selfie,
    begin_task_flow_timer,
    complete_task,
    get_flow_state,
    get_participant_task,
    link_selfie_to_flow,
    record_scan_for_task,
    validate_scan_for_task,
)

router = APIRouter(prefix="/tasks")


def _task_error(exc: AppError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={"code": exc.code, "message": exc.message},
    )


def _selfie_ctx(participant: Participant, pt, task) -> SelfieUploadContext:
    flow = _flow_meta(pt)
    return SelfieUploadContext(
        event_id=participant.event_id,
        participant_id=participant.id,
        task_id=task.id,
        match_id=flow.get("match_id"),
        partner_id=flow.get("partner_id"),
        participant_task_id=pt.id,
    )


def _to_flow_response(result) -> dict:
    return TaskFlowSelfieUploadResponse(
        upload_url=None,
        storage_key=result.storage_key,
        image_url=result.image_url,
        thumbnail_url=result.thumbnail_url,
        selfie_id=result.selfie_id,
        direct_upload=True,
        match_id=result.match_id,
        metadata=result.metadata,
    ).model_dump()


@router.get("/{participant_task_id}/flow")
async def task_flow_state(
    participant_task_id: int,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    pt, task = await get_participant_task(db, participant, participant_task_id)
    try:
        await begin_task_flow_timer(db, pt, task)
        state = get_flow_state(pt, task)
    except TaskCompletionError as e:
        raise _task_error(e) from e
    return ok(TaskFlowStateResponse(**state).model_dump())


@router.post("/{participant_task_id}/flow/validate-scan")
async def task_flow_validate_scan(
    participant_task_id: int,
    body: TaskFlowScanRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    pt, task = await get_participant_task(db, participant, participant_task_id)
    try:
        result = await validate_scan_for_task(db, participant, pt, task, body.qr_payload)
    except TaskCompletionError as e:
        raise _task_error(e) from e
    return ok(TaskFlowValidateScanResponse(**result).model_dump())


@router.post("/{participant_task_id}/flow/scan")
async def task_flow_scan(
    participant_task_id: int,
    body: TaskFlowScanRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    pt, task = await get_participant_task(db, participant, participant_task_id)
    try:
        result = await record_scan_for_task(db, participant, pt, task, body.qr_payload)
    except TaskCompletionError as e:
        raise _task_error(e) from e

    await log_activity(
        db,
        participant.event_id,
        ActivityType.MATCH_CREATED,
        participant.id,
        {
            "partner_id": result["partner_id"],
            "partner_name": result["partner_name"],
            "task_id": task.id,
            "participant_task_id": pt.id,
        },
        summary=f"Scanned {result['partner_name']} for {task.title}",
    )
    return ok(TaskFlowScanResponse(**result).model_dump())


@router.post("/{participant_task_id}/flow/selfie/upload-url")
async def task_flow_selfie_upload_url(
    participant_task_id: int,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """Legacy hook — server-side processing uses multipart upload endpoint."""
    pt, task = await get_participant_task(db, participant, participant_task_id)
    try:
        await assert_flow_ready_for_selfie(pt, task)
    except TaskCompletionError as e:
        raise _task_error(e) from e
    return ok(
        {
            "direct_upload": True,
            "upload_url": None,
            "message": "Upload via POST .../flow/selfie/upload (images are compressed server-side).",
        }
    )


@router.post("/{participant_task_id}/flow/selfie/upload")
async def task_flow_selfie_upload(
    participant_task_id: int,
    file: UploadFile = File(...),
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    pt, task = await get_participant_task(db, participant, participant_task_id)
    try:
        await assert_flow_ready_for_selfie(pt, task)
    except TaskCompletionError as e:
        raise _task_error(e) from e

    data = await file.read()
    try:
        result = await upload_selfie(
            db,
            participant,
            data,
            file.content_type,
            _selfie_ctx(participant, pt, task),
        )
        await link_selfie_to_flow(db, participant, pt, task, result.selfie_id)
    except SelfieStorageError as e:
        raise _task_error(e) from e

    await log_activity(
        db,
        participant.event_id,
        ActivityType.SELFIE_UPLOADED,
        participant.id,
        {
            "selfie_id": result.selfie_id,
            "match_id": result.match_id,
            "task_id": task.id,
        },
        summary=f"Selfie uploaded for {task.title}",
    )
    await emit_selfie_uploaded(
        participant.event_id,
        participant_id=participant.id,
        selfie_id=result.selfie_id,
        task_id=task.id,
        match_id=result.match_id,
        image_url=result.image_url,
        thumbnail_url=result.thumbnail_url,
        display_name=participant.display_name,
        task_title=task.title,
    )
    return ok(_to_flow_response(result))


@router.post("/{participant_task_id}/flow/complete")
async def task_flow_complete(
    participant_task_id: int,
    body: TaskFlowCompleteRequest,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    pt, task = await get_participant_task(db, participant, participant_task_id)
    try:
        result = await complete_task(db, participant, pt, task, body.selfie_id)
    except TaskCompletionError as e:
        raise _task_error(e) from e

    await log_activity(
        db,
        participant.event_id,
        ActivityType.TASK_COMPLETED,
        participant.id,
        {
            "task_id": task.id,
            "participant_task_id": pt.id,
            "selfie_id": body.selfie_id,
            "points": result["points_awarded"],
        },
        summary=f"Completed: {task.title}",
    )
    await emit_task_completed(
        participant.event_id,
        participant_id=participant.id,
        task_id=task.id,
        task_title=task.title,
        points=result["points_awarded"],
        partner_name=result.get("partner_name"),
    )
    return ok(TaskFlowCompleteResponse(**result).model_dump())


@router.post("/{participant_task_id}/toggle")
async def toggle_bingo_task(
    participant_task_id: int,
    participant: Participant = Depends(get_current_participant),
    db: AsyncSession = Depends(get_db),
):
    """Check or uncheck a human-bingo (manual) challenge while the event is live."""
    try:
        result = await toggle_manual_participant_task(db, participant, participant_task_id)
    except (TaskCompletionError, ManualTaskError) as e:
        raise _task_error(e) from e
    return ok(result)
