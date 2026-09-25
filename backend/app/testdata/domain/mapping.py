"""Mapeo de columnas a campos de dominio (RF-22)."""
from __future__ import annotations

import difflib
import hashlib
import unicodedata


def normalize_col(name: str) -> str:
    """Strip, lower, quita tildes y caracteres no alfanuméricos (excepto _)."""
    s = name.strip().lower()
    # Quitar tildes
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode()
    # Quitar todo excepto alfanumérico y guion bajo
    s = "".join(c if c.isalnum() or c == "_" else "_" for c in s)
    # Colapsar guiones bajos múltiples
    while "__" in s:
        s = s.replace("__", "_")
    return s.strip("_")


def header_fingerprint(columns: list[str]) -> str:
    """SHA-256 del join de columnas normalizadas y ordenadas."""
    normalized = sorted(normalize_col(c) for c in columns)
    joined = "|".join(normalized)
    return hashlib.sha256(joined.encode()).hexdigest()


def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()


def suggest_mapping_local(
    columns: list[str],
    domain_fields: list[dict],
) -> dict[str, str | None]:
    """Sugiere mapeo columna → campo de dominio por similitud de nombres.

    domain_fields: [{key, label, synonyms: list[str]}]
    Umbral: 0.6. Si ningún campo supera el umbral, devuelve None para esa columna.
    """
    result: dict[str, str | None] = {}
    for col in columns:
        norm_col = normalize_col(col)
        best_key: str | None = None
        best_score = 0.0
        for df in domain_fields:
            candidates = [normalize_col(df["key"]), normalize_col(df.get("label", ""))]
            for syn in df.get("synonyms") or []:
                candidates.append(normalize_col(syn))
            score = max(_similarity(norm_col, c) for c in candidates if c)
            if score > best_score:
                best_score = score
                best_key = df["key"]
        result[col] = best_key if best_score >= 0.6 else None
    return result
