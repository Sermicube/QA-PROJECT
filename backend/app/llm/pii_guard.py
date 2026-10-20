"""PIIGuard: dos capas de enmascaramiento antes de cualquier envío al LLM.

Capa 1 — regex: números de documento colombiano, correos, teléfonos → [DOC_N]
Capa 2 — NER spaCy es_core_news_md: nombres propios de personas (PER) → [PERSONA_N]

Los nombres nunca llegan al LLM para ser detectados (RNF-01, §6.2 SPEC v2.1).
Si el modelo spaCy no está instalado, capa 2 se omite y se emite una advertencia.
"""
from __future__ import annotations

import re
import structlog
from dataclasses import dataclass
from typing import Any

log = structlog.get_logger()

# ── Capa 1: regex ──────────────────────────────────────────────────────────────

@dataclass
class PIIMatch:
    pattern_name: str
    value: str
    position: int


class PIIDetectedError(ValueError):
    def __init__(self, matches: list[PIIMatch]) -> None:
        self.matches = matches
        types = {m.pattern_name for m in matches}
        super().__init__(f"PII detectado ({', '.join(sorted(types))}) — envío bloqueado")


# Patrones para el contexto colombiano (Ley 1581 de 2012)
_PATTERNS: dict[str, re.Pattern[str]] = {
    "document_number": re.compile(r"\b\d{6,10}\b"),
    "email": re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:3\d{9}|\d{7})\b"),
}

# ── Capa 2: NER spaCy (cargado con lazy loading) ──────────────────────────────

_NLP: Any = None
_NLP_LOADED: bool = False
_NLP_WARNED: bool = False


def _get_nlp() -> Any:
    global _NLP, _NLP_LOADED, _NLP_WARNED
    if _NLP_LOADED:
        return _NLP
    try:
        import spacy  # noqa: PLC0415
        _NLP = spacy.load("es_core_news_md")
        log.info("spacy_model_loaded", model="es_core_news_md")
    except ImportError:
        if not _NLP_WARNED:
            log.warning(
                "spacy_not_installed",
                msg="NER layer disabled — person names may reach the LLM. "
                    "Fix: pip install spacy && python -m spacy download es_core_news_md",
            )
            _NLP_WARNED = True
        _NLP = None
    except OSError:
        if not _NLP_WARNED:
            log.warning(
                "spacy_model_missing",
                model="es_core_news_md",
                msg="NER layer disabled — person names may reach the LLM. "
                    "Fix: python -m spacy download es_core_news_md",
            )
            _NLP_WARNED = True
        _NLP = None
    _NLP_LOADED = True
    return _NLP


def ner_available() -> bool:
    """True if the spaCy model loaded successfully."""
    return _get_nlp() is not None


# ── PIIGuard ───────────────────────────────────────────────────────────────────

class PIIGuard:
    """Detecta y enmascara PII antes de que llegue a un LLM externo (§6.2)."""

    def check(self, text: str) -> list[PIIMatch]:
        """Devuelve todas las coincidencias de la capa regex (capa 1).
        No incluye detección NER — usar mask() para el enmascaramiento completo.
        """
        matches: list[PIIMatch] = []
        for name, pattern in _PATTERNS.items():
            for m in pattern.finditer(text):
                matches.append(PIIMatch(name, m.group(), m.start()))
        return matches

    def assert_clean(self, text: str) -> None:
        """Lanza PIIDetectedError si el texto contiene PII detectada por regex."""
        matches = self.check(text)
        if matches:
            raise PIIDetectedError(matches)

    def mask(self, text: str) -> tuple[str, int]:
        """Enmascara PII en dos capas. Devuelve (texto_enmascarado, total_reemplazos).

        Capa 1: regex → [DOC_N]
        Capa 2: NER spaCy PER → [PERSONA_N]
        """
        doc_counter = [0]

        def _replace_doc(_m: re.Match[str]) -> str:
            doc_counter[0] += 1
            return f"[DOC_{doc_counter[0]}]"

        # Capa 1 — regex
        result = text
        for pattern in _PATTERNS.values():
            result = pattern.sub(_replace_doc, result)

        # Capa 2 — NER spaCy
        nlp = _get_nlp()
        persona_count = 0
        if nlp is not None:
            doc = nlp(result)
            per_spans = [
                (ent.start_char, ent.end_char)
                for ent in doc.ents
                if ent.label_ == "PER"
            ]
            if per_spans:
                # Sort left-to-right; build result in one pass
                per_spans.sort(key=lambda x: x[0])
                parts: list[str] = []
                last_end = 0
                for i, (start, end) in enumerate(per_spans, 1):
                    parts.append(result[last_end:start])
                    parts.append(f"[PERSONA_{i}]")
                    last_end = end
                parts.append(result[last_end:])
                result = "".join(parts)
                persona_count = len(per_spans)

        return result, doc_counter[0] + persona_count
