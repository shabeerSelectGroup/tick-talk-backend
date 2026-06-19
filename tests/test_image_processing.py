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


def test_validate_rejects_empty():
    with pytest.raises(ImageProcessingError) as exc:
        validate_image_upload(b"", "image/jpeg")
    assert exc.value.code == "IMAGE_EMPTY"


def test_validate_rejects_oversized():
    huge = b"x" * (9 * 1024 * 1024)
    with pytest.raises(ImageProcessingError) as exc:
        validate_image_upload(huge, "image/jpeg")
    assert exc.value.code == "IMAGE_TOO_LARGE"
