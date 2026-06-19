"""Selfie image compression and thumbnail generation."""

from __future__ import annotations

import io
from dataclasses import dataclass

from PIL import Image, ImageOps

from app.core.config import get_settings
from app.core.exceptions import AppError

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}


class ImageProcessingError(AppError):
    pass


@dataclass(frozen=True)
class ProcessedSelfieImages:
    image_bytes: bytes
    thumbnail_bytes: bytes
    content_type: str
    width: int
    height: int
    thumbnail_width: int
    thumbnail_height: int
    original_size_bytes: int
    compressed_size_bytes: int
    thumbnail_size_bytes: int


def validate_image_upload(data: bytes, content_type: str | None) -> None:
    settings = get_settings()
    if len(data) == 0:
        raise ImageProcessingError("IMAGE_EMPTY", "Image file is empty.", 400)
    if len(data) > settings.selfie_max_upload_bytes:
        raise ImageProcessingError(
            "IMAGE_TOO_LARGE",
            f"Image exceeds maximum size ({settings.selfie_max_upload_bytes // (1024 * 1024)}MB).",
            413,
        )
    if content_type and content_type.lower() not in ALLOWED_CONTENT_TYPES:
        raise ImageProcessingError(
            "IMAGE_TYPE_UNSUPPORTED",
            "Supported formats: JPEG, PNG, WebP.",
            415,
        )


def process_selfie_image(data: bytes, content_type: str | None = None) -> ProcessedSelfieImages:
    """Compress main image and produce square thumbnail."""
    validate_image_upload(data, content_type)
    settings = get_settings()

    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
    except Exception as e:
        raise ImageProcessingError("IMAGE_INVALID", "Could not read image file.", 400) from e

    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")

    original_size = len(data)
    max_dim = settings.selfie_max_dimension
    thumb_size = settings.selfie_thumbnail_size

    # Thumbnail from full resolution before downscaling the main image
    thumb = img.copy()
    thumb.thumbnail((thumb_size, thumb_size), Image.Resampling.LANCZOS)
    thumb_buf = io.BytesIO()
    thumb.save(thumb_buf, format="JPEG", quality=85, optimize=True)
    thumbnail_bytes = thumb_buf.getvalue()

    img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

    main_buf = io.BytesIO()
    img.save(
        main_buf,
        format="JPEG",
        quality=settings.selfie_jpeg_quality,
        optimize=True,
        progressive=True,
    )
    image_bytes = main_buf.getvalue()

    return ProcessedSelfieImages(
        image_bytes=image_bytes,
        thumbnail_bytes=thumbnail_bytes,
        content_type="image/jpeg",
        width=img.width,
        height=img.height,
        thumbnail_width=thumb.width,
        thumbnail_height=thumb.height,
        original_size_bytes=original_size,
        compressed_size_bytes=len(image_bytes),
        thumbnail_size_bytes=len(thumbnail_bytes),
    )
