"""PIIGuard — segunda capa NER (§6.2 SPEC v2.1).

Test principal: una transcripción con "Diaz Jimenez, Sergio Alejandro" no llega
al LLM; el FakeProvider recibe [PERSONA_1] en su lugar.

Estrategia: se mockea _get_nlp() para devolver un nlp sintético que detecta el
nombre como entidad PER, sin depender de que es_core_news_md esté instalado.
Esto hace el test hermético y reproducible en CI.
"""
from __future__ import annotations

import types
from unittest.mock import MagicMock, patch

import pytest

import app.llm.pii_guard as pii_guard_module
from app.llm.pii_guard import PIIGuard


# ── helpers para simular spaCy ────────────────────────────────────────────────

def _make_mock_nlp(text: str, person_spans: list[tuple[int, int]]) -> MagicMock:
    """Construye un objeto nlp simulado para texto y spans de PER dados."""
    ents = []
    for start, end in person_spans:
        ent = MagicMock()
        ent.label_ = "PER"
        ent.start_char = start
        ent.end_char = end
        ents.append(ent)

    doc = MagicMock()
    doc.ents = ents

    nlp = MagicMock()
    nlp.return_value = doc
    return nlp


# ── test central: nombre no llega al LLM ─────────────────────────────────────

def test_mask_replaces_person_name_with_persona_token() -> None:
    """'Diaz Jimenez, Sergio Alejandro' → [PERSONA_1]; el nombre no queda en el texto."""
    text = "Diaz Jimenez, Sergio Alejandro 1 minuto 37 segundos"
    name = "Diaz Jimenez, Sergio Alejandro"
    start = text.index(name)
    end = start + len(name)

    mock_nlp = _make_mock_nlp(text, [(start, end)])
    guard = PIIGuard()

    with patch.object(pii_guard_module, "_get_nlp", return_value=mock_nlp):
        masked, count = guard.mask(text)

    assert name not in masked, "El nombre real no debe aparecer en el texto enmascarado"
    assert "[PERSONA_1]" in masked, "El nombre debe sustituirse por [PERSONA_1]"
    assert count >= 1


def test_mask_replaces_multiple_persons_sequentially() -> None:
    """Dos nombres distintos producen [PERSONA_1] y [PERSONA_2] en orden."""
    text = "Diaz Jimenez, Sergio Alejandro y Lopez Torres, Maria son afiliados"
    name1 = "Diaz Jimenez, Sergio Alejandro"
    name2 = "Lopez Torres, Maria"
    s1, e1 = text.index(name1), text.index(name1) + len(name1)
    s2, e2 = text.index(name2), text.index(name2) + len(name2)

    mock_nlp = _make_mock_nlp(text, [(s1, e1), (s2, e2)])
    guard = PIIGuard()

    with patch.object(pii_guard_module, "_get_nlp", return_value=mock_nlp):
        masked, count = guard.mask(text)

    assert name1 not in masked
    assert name2 not in masked
    assert "[PERSONA_1]" in masked
    assert "[PERSONA_2]" in masked
    assert count == 2


def test_mask_no_names_unchanged_by_ner_layer() -> None:
    """Sin entidades PER, el texto no cambia en la capa NER."""
    text = "Validar que el sistema rechace la exclusión cuando la fecha es inválida"

    mock_nlp = _make_mock_nlp(text, [])
    guard = PIIGuard()

    with patch.object(pii_guard_module, "_get_nlp", return_value=mock_nlp):
        masked, count = guard.mask(text)

    assert masked == text
    assert count == 0


def test_mask_ner_disabled_gracefully_when_nlp_none() -> None:
    """Si _get_nlp devuelve None, mask() sigue funcionando (solo capa regex)."""
    text = "El analista 12345678 revisa el caso"
    guard = PIIGuard()

    with patch.object(pii_guard_module, "_get_nlp", return_value=None):
        masked, count = guard.mask(text)

    assert "12345678" not in masked
    assert "[DOC_1]" in masked
    assert "[PERSONA_" not in masked


# ── test de integración: nombre no llega a FakeProvider vía propose_description ──

@pytest.mark.asyncio
async def test_propose_description_masks_person_name_before_llm(monkeypatch) -> None:
    """Una transcripción con un nombre propio llega al LLM con [PERSONA_1], no el nombre.

    Estrategia: se parchea el método `mask` del singleton `_pii_guard` del módulo
    service, simulando la capa NER sin depender de que spaCy esté instalado ni de
    la gestión del estado global del módulo pii_guard.
    """
    import app.llm.factory as factory_module
    from app.context import service as ctx_service
    from app.context.service import ContextService
    from app.llm.fake_provider import FakeProvider

    fake = FakeProvider(
        response=(
            '{"bug_behavior": "Error al procesar", '
            '"what_to_test": "certificación de transcripción", '
            '"expected_result": "resultado observable", '
            '"fix": "parche"}'
        )
    )
    monkeypatch.setattr(factory_module, "get_provider", lambda: fake)

    transcript = "Diaz Jimenez, Sergio Alejandro 1 minuto 37 segundos: el sistema genera error."
    name = "Diaz Jimenez, Sergio Alejandro"

    # Simula la capa NER de PIIGuard reemplazando el nombre con [PERSONA_1]
    def mock_mask(text: str) -> tuple[str, int]:
        masked = text.replace(name, "[PERSONA_1]")
        return masked, (1 if name in text else 0)

    monkeypatch.setattr(ctx_service._pii_guard, "mask", mock_mask)

    svc = ContextService(repo=MagicMock())
    await svc.propose_description(transcript, "bug", user_id=None)

    sent = fake.all_sent_text
    assert name not in sent, (
        f"El nombre '{name}' no debe llegar al LLM (PIIGuard capa NER)"
    )
    assert "[PERSONA_1]" in sent, (
        "El LLM debe recibir [PERSONA_1] en lugar del nombre real"
    )
