"""Validación OCR de pantallazos (RF-32, §6.8).

El texto OCR nunca se envía al LLM — puede contener datos de afiliados.
En desarrollo sin Tesseract, degrada elegantemente a status='warning'.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Regexes de búsqueda
_TIME_RE = re.compile(
    r"\b([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?\s*(?:a\.?m\.?|p\.?m\.?)?\b",
    re.IGNORECASE,
)
_URL_RE = re.compile(
    r"https?://[^\s\"'<>]+|(?:www\.|(?:[a-zA-Z0-9-]+\.)+(?:com|net|org|co|gov|edu))[^\s\"'<>]*",
    re.IGNORECASE,
)


@dataclass
class OcrResult:
    status: str            # valid | warning | rejected
    time_found: bool
    url_found: bool
    time_value: str | None
    url_value: str | None
    confidence: float      # 0.0–1.0
    raw_text: str | None   # NUNCA se envía al LLM


def _crop_region(img: object, region: str) -> object:
    """Recorta 'bottom_right' (reloj) o 'top_strip' (barra URL) de la imagen."""
    w, h = img.size  # type: ignore[attr-defined]
    if region == "bottom_right":
        return img.crop((w // 2, int(h * 0.75), w, h))  # type: ignore[attr-defined]
    if region == "top_strip":
        return img.crop((0, 0, w, min(h, int(h * 0.12) + 30)))  # type: ignore[attr-defined]
    return img


def _search_text(text: str) -> tuple[str | None, str | None]:
    """Devuelve (time_value, url_value) encontrados en el texto."""
    tm = _TIME_RE.search(text)
    um = _URL_RE.search(text)
    return (tm.group(0) if tm else None, um.group(0) if um else None)


def validate_screenshot(image_bytes: bytes) -> OcrResult:
    """Valida que el pantallazo contenga hora del sistema y URL del navegador.

    Degrada a warning si Pillow o Tesseract no están instalados.
    """
    # Intentar cargar Pillow
    try:
        from PIL import Image, ImageFilter, ImageOps
        import io
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return OcrResult(
            status="warning",
            time_found=False,
            url_found=False,
            time_value=None,
            url_value=None,
            confidence=0.0,
            raw_text=None,
        )

    # Intentar OCR con Tesseract
    try:
        import pytesseract

        def _ocr(pil_img: object) -> str:
            gray = ImageOps.grayscale(pil_img)  # type: ignore[arg-type]
            enhanced = gray.filter(ImageFilter.SHARPEN)
            return pytesseract.image_to_string(enhanced, lang="spa+eng")

        # Buscar hora en esquina inferior derecha primero
        bottom_right_text = _ocr(_crop_region(img, "bottom_right"))
        time_val, _ = _search_text(bottom_right_text)

        # Buscar URL en franja superior primero
        top_text = _ocr(_crop_region(img, "top_strip"))
        _, url_val = _search_text(top_text)

        # Si no encontró en recortes, buscar en imagen completa
        full_text = ""
        if not time_val or not url_val:
            full_text = _ocr(img)
            if not time_val:
                time_val, _ = _search_text(full_text)
            if not url_val:
                _, url_val = _search_text(full_text)

        raw = (bottom_right_text + "\n" + top_text + "\n" + full_text).strip()
        time_found = time_val is not None
        url_found = url_val is not None

        if time_found and url_found:
            status = "valid"
            confidence = 1.0
        elif time_found or url_found:
            status = "warning"
            confidence = 0.5
        else:
            status = "rejected"
            confidence = 0.0

        return OcrResult(
            status=status,
            time_found=time_found,
            url_found=url_found,
            time_value=time_val,
            url_value=url_val,
            confidence=confidence,
            raw_text=raw,
        )

    except Exception:
        # Tesseract no instalado o falla — degradar a warning
        return OcrResult(
            status="warning",
            time_found=False,
            url_found=False,
            time_value=None,
            url_value=None,
            confidence=0.0,
            raw_text=None,
        )
