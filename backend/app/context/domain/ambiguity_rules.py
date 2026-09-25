"""Reglas locales de detección de ambigüedades (RF-13, §6.3).

Estas reglas son determinísticas y no requieren LLM.
El LLM se usa solo para: ramas faltantes, contradicciones semánticas,
condiciones sin resultado definido.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class AmbiguityFinding:
    type: str          # boundary_undefined | implicit_unit | vague_term
    fragment: str      # fragmento del texto donde se detectó
    location: str      # fuente + sección
    explanation: str
    question: str


# ────────────────────────────────────────────────────────────────────────────
# Patrones
# ────────────────────────────────────────────────────────────────────────────

# Comparadores que implican frontera sin aclararla: "mayor que X" pero ¿qué pasa si es igual?
_BOUNDARY_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\b(mayor\s+(?:o\s+igual\s+)?(?:a|que))\b",
        r"\b(menor\s+(?:o\s+igual\s+)?(?:a|que))\b",
        r"\b(anterior\s+(?:a|al))\b",
        r"\b(posterior\s+(?:a|al))\b",
        r"\b(superior\s+(?:a|al))\b",
        r"\b(inferior\s+(?:a|al))\b",
        r"\b(después\s+de)\b",
        r"\b(antes\s+de)\b",
        r"\b(a\s+partir\s+de)\b",
        r"\b(hasta\s+(?:el|la|los|las)?)\b",
        r"\b(desde\s+(?:el|la|los|las)?)\b",
    ]
]

# "N días" sin especificar si son hábiles o calendario
_IMPLICIT_UNIT = re.compile(
    r"\b(\d+)\s+d[ií]as?\b(?!\s+(?:h[áa]biles?|calendario|naturales?))",
    re.IGNORECASE,
)

# Términos vagos
_VAGUE_TERMS = re.compile(
    r"\b(seg[úu]n\s+corresponda|si\s+aplica|eventualmente|algunos|adecuadamente|"
    r"correctamente|de\s+forma\s+exitosa|de\s+manera\s+correcta|en\s+caso\s+necesario|"
    r"cuando\s+sea\s+necesario)\b",
    re.IGNORECASE,
)

# "mayor que" / "menor que" sin "o igual" — el caso igual queda sin definir
_STRICT_BOUNDARY = re.compile(
    r"\b(mayor\s+que|menor\s+que|superior\s+que|inferior\s+que|"
    r"mayor\s+a(?!\s+o\s+igual)|menor\s+a(?!\s+o\s+igual))\b",
    re.IGNORECASE,
)


# ────────────────────────────────────────────────────────────────────────────
# Función principal
# ────────────────────────────────────────────────────────────────────────────

def scan_text(text: str, location: str) -> list[AmbiguityFinding]:
    """Analiza *text* y devuelve hallazgos de ambigüedad."""
    findings: list[AmbiguityFinding] = []
    seen_fragments: set[str] = set()

    def _add(finding: AmbiguityFinding) -> None:
        key = (finding.type, finding.fragment[:60])
        if key not in seen_fragments:
            seen_fragments.add(key)
            findings.append(finding)

    for match in _STRICT_BOUNDARY.finditer(text):
        fragment = _context_window(text, match)
        _add(AmbiguityFinding(
            type="boundary_undefined",
            fragment=fragment,
            location=location,
            explanation=(
                f"La expresión '{match.group()}' no define el caso igual: "
                "¿qué ocurre cuando los valores son exactamente iguales?"
            ),
            question=(
                f"Cuando los valores son exactamente iguales, "
                f"¿el sistema debe {_infer_action(match.group())}?"
            ),
        ))

    for match in _IMPLICIT_UNIT.finditer(text):
        fragment = _context_window(text, match)
        _add(AmbiguityFinding(
            type="implicit_unit",
            fragment=fragment,
            location=location,
            explanation=(
                f"'{match.group()}' no especifica si son días hábiles o calendario."
            ),
            question=(
                f"Los {match.group(1)} días mencionados, ¿son días hábiles (sin festivos) "
                "o días calendario?"
            ),
        ))

    for match in _VAGUE_TERMS.finditer(text):
        fragment = _context_window(text, match)
        _add(AmbiguityFinding(
            type="vague_term",
            fragment=fragment,
            location=location,
            explanation=(
                f"El término '{match.group()}' es ambiguo y no define un comportamiento concreto."
            ),
            question=(
                f"¿Qué comportamiento exacto del sistema describe '{match.group()}'? "
                "¿Hay una regla de negocio específica que lo determine?"
            ),
        ))

    return findings


def scan_sources(sources: list[dict]) -> list[AmbiguityFinding]:
    """Escanea múltiples fuentes de contexto.

    Cada fuente debe tener: kind (str), text (str), sections (list[dict] opcional).
    """
    findings: list[AmbiguityFinding] = []
    for src in sources:
        kind = src.get("kind", "unknown")
        sections: list[dict] = src.get("sections") or []
        full_text: str = src.get("text") or ""

        if sections:
            for sec in sections:
                loc = f"{kind} › {sec.get('title', '?')}"
                findings.extend(scan_text(sec.get("content", ""), loc))
        elif full_text:
            findings.extend(scan_text(full_text, kind))

    return findings


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _context_window(text: str, match: re.Match, window: int = 80) -> str:
    """Devuelve ~window caracteres alrededor del match."""
    start = max(0, match.start() - window // 2)
    end = min(len(text), match.end() + window // 2)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet


def _infer_action(comparator: str) -> str:
    comp = comparator.lower()
    if "mayor" in comp or "superior" in comp:
        return "comportarse igual que cuando es mayor"
    if "menor" in comp or "inferior" in comp:
        return "comportarse igual que cuando es menor"
    return "permitir o rechazar la operación"
