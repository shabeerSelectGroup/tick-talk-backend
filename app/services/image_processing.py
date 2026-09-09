"""Selfie image compression and thumbnail generation."""

from __future__ import annotations

import base64
import io
import os
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFont, ImageOps

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


_FONT_CANDIDATES = (
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
)


def _load_font(size: int):
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_name_sign_card(name: str, sign: str | None = None) -> bytes:
    """JPEG card used when a task is completed with a name instead of a photo."""
    size = 1080
    margin = 80
    img = Image.new("RGB", (size, size), "#0f766e")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (48, 48, size - 48, size - 48),
        radius=48,
        fill="#042f2e",
        outline="#5eead4",
        width=6,
    )

    label_font = _load_font(36)
    name_font = _load_font(72)
    sign_font = _load_font(44)
    inner_width = size - margin * 2

    label = "MET"
    label_w = draw.textlength(label, font=label_font)
    draw.text(((size - label_w) / 2, 180), label, fill="#5eead4", font=label_font)

    name_lines = _wrap_text(draw, name.strip(), name_font, inner_width)
    y = 280
    for line in name_lines[:4]:
        line_w = draw.textlength(line, font=name_font)
        draw.text(((size - line_w) / 2, y), line, fill="#f8fafc", font=name_font)
        y += 92

    cleaned_sign = (sign or "").strip()
    if cleaned_sign.startswith("data:image"):
        y += 16
        _paste_signature_image(img, cleaned_sign, y=y, max_width=inner_width, max_height=260)
    elif cleaned_sign:
        y += 24
        sign_lines = _wrap_text(draw, cleaned_sign, sign_font, inner_width)
        for line in sign_lines[:3]:
            line_w = draw.textlength(line, font=sign_font)
            draw.text(((size - line_w) / 2, y), line, fill="#99f6e4", font=sign_font)
            y += 58

    brand = "Tick Talk"
    brand_w = draw.textlength(brand, font=label_font)
    draw.text(((size - brand_w) / 2, size - 160), brand, fill="#5eead4", font=label_font)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90, optimize=True)
    return buf.getvalue()


def _paste_signature_image(card: Image.Image, data_url: str, *, y: int, max_width: int, max_height: int) -> None:
    try:
        _, encoded = data_url.split(",", 1)
        raw = base64.b64decode(encoded)
        signature = Image.open(io.BytesIO(raw)).convert("RGBA")
    except Exception:
        return
    signature.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
    x = (card.width - signature.width) // 2
    card.paste(signature, (x, y), signature)
