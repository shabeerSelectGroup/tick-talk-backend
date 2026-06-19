import base64
import io

import qrcode
from qrcode.constants import ERROR_CORRECT_M


def generate_qr_data_url(payload: str, size: int = 280) -> str:
    """Return a PNG data URL suitable for <img src>."""
    qr = qrcode.QRCode(version=1, error_correction=ERROR_CORRECT_M, box_size=10, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="#ffffff")
    img = img.resize((size, size))

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def generate_qr_png_bytes(payload: str, size: int = 512) -> bytes:
    """PNG bytes for download responses."""
    qr = qrcode.QRCode(version=1, error_correction=ERROR_CORRECT_M, box_size=10, border=2)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="#ffffff")
    img = img.resize((size, size))
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
