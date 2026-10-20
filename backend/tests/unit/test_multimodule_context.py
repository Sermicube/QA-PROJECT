"""
Tests de generalidad de dominio — RF-12, RF-13.

Verifica que el pipeline de análisis de contexto funciona correctamente para tres
módulos distintos de Beyond Health (contratos, incapacidades, recaudo/PILA) y que
cada módulo produce contexto con su propia terminología, sin arrastrar términos de
otros módulos.

También verifica _parse_json_array (nuevo helper) con respuestas con y sin markdown.
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock

from app.context.service import ContextService
from app.llm.fake_provider import FakeProvider
from app.llm.pii_guard import PIIGuard


# ── Fixtures de contexto por módulo ────────────────────────────────────────────

CONTRATOS_DESC = (
    "Se certifica la brecha de exclusión de beneficiario en el módulo de contratos. "
    "Cuando el analista excluye un beneficiario de un contrato, el sistema debe validar "
    "que la fecha de efecto de la exclusión no sea anterior a 6 meses desde hoy. "
    "Si la fecha viola la restricción temporal, el sistema debe retornar E-001 y "
    "no registrar la exclusión."
)

INCAPACIDADES_DESC = (
    "Brecha 996: el servicio de consulta de incapacidades con tipos de consulta 3 y 4 "
    "no retornaba incapacidades en estado ingresado porque no tenían empleador marcado "
    "antes del análisis. La brecha resuelve esto guardando el empleador en una tabla "
    "temporal al momento de crear la incapacidad. El servicio tipo 3 y 4 debe consultar "
    "esa tabla temporal para retornar correctamente las incapacidades asociadas."
)

RECAUDO_DESC = (
    "Se certifica el cargue masivo de archivos PILA en el módulo de recaudo. "
    "Cuando el operador sube un archivo de liquidación, el sistema valida el tipo de "
    "cotizante y el período reportado. Si el tipo de cotizante PC no está habilitado "
    "para el período liquidado, el sistema debe rechazar el registro y retornar E-043."
)

# Términos que deben aparecer en el contexto de cada módulo
CONTRATOS_TERMS = {"beneficiario", "contrato", "exclusión"}
INCAPACIDADES_TERMS = {"incapacidad", "empleador", "tabla temporal"}
RECAUDO_TERMS = {"pila", "cotizante", "cargue"}

# Términos que NO deben aparecer en el contexto de un módulo distinto
CONTRATOS_FORBIDDEN_IN_OTHERS = {"beneficiario"}
INCAPACIDADES_FORBIDDEN_IN_OTHERS = {"incapacidad"}
RECAUDO_FORBIDDEN_IN_OTHERS = {"cotizante", "pila"}


def _make_analyst_source(free_text: str):
    """Crea un stub de ContextSource tipo analyst_description."""
    src = MagicMock()
    src.kind = "analyst_description"
    src.content = {"free_text": free_text}
    src.extracted_text = None
    src.sections = []
    return src


# ── Tests de construcción de contexto ──────────────────────────────────────────


def _build_context(free_text: str) -> str:
    svc = ContextService(repo=MagicMock())
    source = _make_analyst_source(free_text)
    return svc._build_context_text([source])


def test_contratos_context_contains_module_terms():
    ctx = _build_context(CONTRATOS_DESC)
    ctx_low = ctx.lower()
    for term in CONTRATOS_TERMS:
        assert term in ctx_low, f"Contexto contratos debe contener '{term}'"


def test_incapacidades_context_contains_module_terms():
    ctx = _build_context(INCAPACIDADES_DESC)
    ctx_low = ctx.lower()
    for term in INCAPACIDADES_TERMS:
        assert term in ctx_low, f"Contexto incapacidades debe contener '{term}'"


def test_recaudo_context_contains_module_terms():
    ctx = _build_context(RECAUDO_DESC)
    ctx_low = ctx.lower()
    for term in RECAUDO_TERMS:
        assert term in ctx_low, f"Contexto recaudo debe contener '{term}'"


def test_contratos_context_does_not_bleed_incapacidades_terms():
    ctx = _build_context(CONTRATOS_DESC).lower()
    for term in INCAPACIDADES_FORBIDDEN_IN_OTHERS:
        assert term not in ctx, f"Contexto contratos NO debe contener '{term}' (término de incapacidades)"


def test_incapacidades_context_does_not_bleed_recaudo_terms():
    ctx = _build_context(INCAPACIDADES_DESC).lower()
    for term in RECAUDO_FORBIDDEN_IN_OTHERS:
        assert term not in ctx, f"Contexto incapacidades NO debe contener '{term}' (término de recaudo)"


def test_recaudo_context_does_not_bleed_contratos_terms():
    ctx = _build_context(RECAUDO_DESC).lower()
    for term in CONTRATOS_FORBIDDEN_IN_OTHERS:
        assert term not in ctx, f"Contexto recaudo NO debe contener '{term}' (término de contratos)"


# ── PIIGuard sobre contextos de módulo ─────────────────────────────────────────


@pytest.mark.parametrize("desc,label", [
    (CONTRATOS_DESC, "contratos"),
    (INCAPACIDADES_DESC, "incapacidades"),
    (RECAUDO_DESC, "recaudo"),
])
def test_pii_guard_passes_module_context(desc: str, label: str):
    """Texto de contexto de negocio (sin PII real) debe pasar PIIGuard sin excepción."""
    import re
    guard = PIIGuard()
    masked, _count = guard.mask(desc)
    assert masked, f"PIIGuard devolvió texto vacío para módulo {label}"
    # Ningún número de 8-12 dígitos (documento) ni correo debe haber en el texto de negocio
    assert not re.search(r"\b\d{8,12}\b", desc), (
        f"Fixture de {label} contiene un número que parece documento de identidad"
    )
    assert "@" not in desc, f"Fixture de {label} contiene un correo electrónico"


# ── FakeProvider spy: qué llega al LLM ─────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("desc,expected_terms,label", [
    (CONTRATOS_DESC, CONTRATOS_TERMS, "contratos"),
    (INCAPACIDADES_DESC, INCAPACIDADES_TERMS, "incapacidades"),
    (RECAUDO_DESC, RECAUDO_TERMS, "recaudo"),
])
async def test_fake_provider_receives_correct_module_context(
    desc: str, expected_terms: set, label: str, monkeypatch
):
    """El texto enviado al LLM debe contener los términos del módulo correcto."""
    import app.llm.factory as factory_module
    fake = FakeProvider()
    monkeypatch.setattr(factory_module, "get_provider", lambda: fake)

    svc = ContextService(repo=MagicMock())

    await svc.propose_description(desc, "brecha", user_id=None)

    assert len(fake.calls) == 1
    sent_text = fake.all_sent_text.lower()
    for term in expected_terms:
        assert term in sent_text, (
            f"LLM para módulo {label} debe recibir el término '{term}' en el contexto"
        )


# ── _parse_json_array: manejo de markdown y JSON plano ─────────────────────────


def test_parse_json_array_plain():
    from app.context.tasks import _parse_json_array
    raw = '[{"code": "CA-01", "text": "Regla"}]'
    result = _parse_json_array(raw)
    assert len(result) == 1
    assert result[0]["code"] == "CA-01"


def test_parse_json_array_with_markdown_fence():
    from app.context.tasks import _parse_json_array
    raw = '```json\n[{"type": "missing_branch", "question": "¿Qué pasa?"}]\n```'
    result = _parse_json_array(raw)
    assert len(result) == 1
    assert result[0]["type"] == "missing_branch"


def test_parse_json_array_with_text_around():
    from app.context.tasks import _parse_json_array
    raw = 'Aquí están las ambigüedades:\n[{"type": "vague_term", "question": "¿Qué?"}]\nEso es todo.'
    result = _parse_json_array(raw)
    assert len(result) == 1


def test_parse_json_array_returns_empty_on_invalid():
    from app.context.tasks import _parse_json_array
    assert _parse_json_array("No hay JSON aquí") == []
    assert _parse_json_array("") == []
    assert _parse_json_array("```json\n{}\n```") == []  # object, not array


def test_parse_json_array_real_llm_style():
    """Simula la respuesta real de Anthropic: fenced JSON con varios items."""
    from app.context.tasks import _parse_json_array
    raw = (
        'Aquí detecto las siguientes ambigüedades:\n\n'
        '```json\n'
        '[\n'
        '  {"type": "missing_branch", "fragment": "Si válido", '
        '"location": "desc", "explanation": "Falta rama", "question": "¿Qué pasa?"},\n'
        '  {"type": "undefined_result", "fragment": "retorna error", '
        '"location": "desc", "explanation": "Código no especificado", "question": "¿Cuál código?"}\n'
        ']\n'
        '```'
    )
    result = _parse_json_array(raw)
    assert len(result) == 2
    assert result[0]["type"] == "missing_branch"
    assert result[1]["type"] == "undefined_result"
