import base64
import io

import pytest
from PIL import Image

from app.services.image_processing import (
    ImageProcessingError,
    process_selfie_image,
    validate_image_upload,
)


def _jpeg_bytes(width: int = 800, height: int = 600) -> bytes:
    img = Image.new("RGB", (width, height), color=(10, 120, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_process_selfie_compresses_and_thumbnails():
    raw = _jpeg_bytes(2400, 1800)
    result = process_selfie_image(raw, "image/jpeg")
    assert result.content_type == "image/jpeg"
    assert result.compressed_size_bytes < result.original_size_bytes
    assert result.thumbnail_size_bytes < result.compressed_size_bytes
    assert result.width <= 1920
    assert result.height <= 1920
    assert result.thumbnail_width <= 480


def test_render_name_sign_card_is_jpeg():
    from app.services.image_processing import render_name_sign_card

    data = render_name_sign_card("Alex Kim", "AK")
    img = Image.open(io.BytesIO(data))
    assert img.format == "JPEG"
    assert img.size == (1080, 1080)


def test_render_name_sign_card_accepts_drawn_signature():
    from app.services.image_processing import render_name_sign_card

    mark = Image.new("RGB", (200, 80), color=(255, 255, 255))
    buf = io.BytesIO()
    mark.save(buf, format="PNG")

    data_url = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    data = render_name_sign_card("Sam Lee", data_url)
    img = Image.open(io.BytesIO(data))
    assert img.format == "JPEG"
    assert img.size == (1080, 1080)


def test_complete_request_accepts_name_without_selfie():
    from app.schemas.task_flow import TaskFlowCompleteRequest

    body = TaskFlowCompleteRequest(partner_name="Sam Lee", partner_sign="SL")
    assert body.selfie_id is None
    assert body.partner_name == "Sam Lee"
    assert body.partner_sign == "SL"


def test_complete_request_requires_selfie_or_name():
    from pydantic import ValidationError

    from app.schemas.task_flow import TaskFlowCompleteRequest

    with pytest.raises(ValidationError):
        TaskFlowCompleteRequest()
    with pytest.raises(ValidationError):
        TaskFlowCompleteRequest(partner_name="A")


def test_validate_rejects_empty():
    with pytest.raises(ImageProcessingError) as exc:
        validate_image_upload(b"", "image/jpeg")
    assert exc.value.code == "IMAGE_EMPTY"


def test_validate_rejects_oversized():
    huge = b"x" * (21 * 1024 * 1024)
    with pytest.raises(ImageProcessingError) as exc:
        validate_image_upload(huge, "image/jpeg")
    assert exc.value.code == "IMAGE_TOO_LARGE"


def test_validate_accepts_library_content_types():
    raw = _jpeg_bytes()
    validate_image_upload(raw, "image/jpeg; charset=binary")
    validate_image_upload(raw, "application/octet-stream")
    validate_image_upload(raw, None)
    validate_image_upload(raw, "")
    process_selfie_image(raw, "application/octet-stream")
    process_selfie_image(raw, "image/jpeg; charset=utf-8")


def test_validate_rejects_non_image_content_type():
    with pytest.raises(ImageProcessingError) as exc:
        validate_image_upload(_jpeg_bytes(), "video/mp4")
    assert exc.value.code == "IMAGE_TYPE_UNSUPPORTED"


def test_process_png_from_photo_library():
    img = Image.new("RGBA", (640, 480), color=(10, 120, 200, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    result = process_selfie_image(buf.getvalue(), "image/png")
    assert result.content_type == "image/jpeg"
    assert result.width == 640
    assert result.height == 480
