"""Turn a downloaded cover into a JPEG readers can embed."""

from __future__ import annotations

import io


def to_jpeg(data: bytes) -> bytes | None:
    if not data:
        return None
    try:
        from PIL import Image
    except ImportError:
        return data if data.startswith(b"\xff\xd8") else None
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
    except Exception:
        return None
    if image.mode != "RGB":
        image = image.convert("RGB")
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()
