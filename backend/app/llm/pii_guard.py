import re
from dataclasses import dataclass


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
# document_number: CC / TI / NIT / NUI — 6 a 10 dígitos
# email: correo electrónico estándar
# phone: celular colombiano (3XXXXXXXXX) o fijo de 7 dígitos
_PATTERNS: dict[str, re.Pattern[str]] = {
    "document_number": re.compile(r"\b\d{6,10}\b"),
    "email": re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
    "phone": re.compile(r"\b(?:3\d{9}|\d{7})\b"),
}


class PIIGuard:
    """Detecta y enmascara PII antes de que llegue a un LLM externo."""

    def check(self, text: str) -> list[PIIMatch]:
        matches: list[PIIMatch] = []
        for name, pattern in _PATTERNS.items():
            for m in pattern.finditer(text):
                matches.append(PIIMatch(name, m.group(), m.start()))
        return matches

    def assert_clean(self, text: str) -> None:
        """Lanza PIIDetectedError si el texto contiene PII."""
        matches = self.check(text)
        if matches:
            raise PIIDetectedError(matches)

    def mask(self, text: str) -> tuple[str, int]:
        """Reemplaza PII por tokens [DOC_N]. Devuelve (texto_enmascarado, cantidad)."""
        counter = [0]

        def replace(_m: re.Match[str]) -> str:
            counter[0] += 1
            return f"[DOC_{counter[0]}]"

        result = text
        for pattern in _PATTERNS.values():
            result = pattern.sub(replace, result)

        return result, counter[0]
