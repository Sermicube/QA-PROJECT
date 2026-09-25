"""Tests para app.evidence.domain.ocr (RF-32)."""
import re
from unittest.mock import patch

import pytest

from app.evidence.domain.ocr import OcrResult, _TIME_RE, _URL_RE, validate_screenshot


# ── Helpers para crear imágenes sintéticas ────────────────────────────────────

def _make_image_bytes(text: str) -> bytes:
    """Genera una imagen PNG simple con texto usando Pillow."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        import io
        img = Image.new("RGB", (800, 600), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), text, fill=(0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()
    except ImportError:
        pytest.skip("Pillow no disponible")


# ── Tests de regexes ──────────────────────────────────────────────────────────

class TestTimeRegex:
    def test_matches_hhmm(self):
        assert _TIME_RE.search("Sistema: 14:35")

    def test_matches_hhmmss(self):
        assert _TIME_RE.search("Hora 09:05:22")

    def test_matches_with_am(self):
        assert _TIME_RE.search("02:30 p.m.")

    def test_no_match_invalid(self):
        assert not _TIME_RE.search("código 999:99")

    def test_no_match_only_letters(self):
        assert not _TIME_RE.search("sin hora aquí")


class TestUrlRegex:
    def test_matches_https(self):
        assert _URL_RE.search("URL: https://beyond.health.sonda.com/afiliados")

    def test_matches_http(self):
        assert _URL_RE.search("http://localhost:8000/api/v1/test")

    def test_matches_www(self):
        assert _URL_RE.search("www.ejemplo.com")

    def test_no_match_plain_text(self):
        assert not _URL_RE.search("solo texto sin url")


# ── Tests de validate_screenshot ─────────────────────────────────────────────

class TestValidateScreenshot:
    def test_tesseract_unavailable_returns_warning(self):
        """Si pytesseract no está instalado, devuelve warning sin crash."""
        img_bytes = _make_image_bytes("14:35 https://beyond.sonda.com")
        with patch.dict("sys.modules", {"pytesseract": None}):
            result = validate_screenshot(img_bytes)
        assert result.status == "warning"
        assert result.confidence == 0.0

    def test_pillow_unavailable_returns_warning(self):
        """Si Pillow no está disponible, devuelve warning."""
        with patch.dict("sys.modules", {"PIL": None, "PIL.Image": None}):
            result = validate_screenshot(b"not_an_image")
        assert result.status == "warning"

    def test_invalid_bytes_returns_warning(self):
        """Bytes que no son imagen → warning, no crash."""
        result = validate_screenshot(b"\x00\x01\x02corrupted")
        assert result.status in ("warning", "rejected")

    def test_empty_bytes_returns_warning(self):
        result = validate_screenshot(b"")
        assert result.status in ("warning", "rejected")

    def test_result_fields_present(self):
        """OcrResult siempre tiene todos los campos."""
        result = validate_screenshot(b"")
        assert hasattr(result, "status")
        assert hasattr(result, "time_found")
        assert hasattr(result, "url_found")
        assert hasattr(result, "confidence")
        assert result.status in ("valid", "warning", "rejected")

    def test_raw_text_not_sent_to_llm(self):
        """raw_text es solo para logs internos — test documental."""
        result = validate_screenshot(b"")
        # raw_text puede ser None o str, pero nunca debe pasarse al LLM
        assert result.raw_text is None or isinstance(result.raw_text, str)
