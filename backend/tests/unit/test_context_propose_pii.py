"""
Test: PIIGuard enmascara cédulas antes de que el texto llegue al LLM.

RF-10 / PIIGuard: ningún dato de documento de identidad debe llegar al LLM.
La función propose_description() debe pasar el texto libre por PIIGuard y
enviar solo el texto enmascarado al proveedor LLM.
"""

import pytest
from unittest.mock import MagicMock

import app.llm.factory as factory_module
from app.context.service import ContextService
from app.llm.fake_provider import FakeProvider


@pytest.mark.asyncio
async def test_propose_description_masks_cedula_before_llm(monkeypatch):
    """Una cédula de 10 dígitos debe llegar al LLM como [DOC_1], no como el número original."""
    fake = FakeProvider(
        response=(
            '{"bug_behavior": "Error 500 al excluir", '
            '"what_to_test": "exclusión de beneficiario", '
            '"expected_result": "exclusión correcta", '
            '"fix": "parche aplicado"}'
        )
    )

    # patch get_provider en el módulo factory, que es lo que importa propose_description()
    monkeypatch.setattr(factory_module, "get_provider", lambda: fake)

    svc = ContextService(repo=MagicMock())

    await svc.propose_description(
        "El sistema genera error 500 cuando el afiliado cédula 1098765432 intenta excluir un beneficiario.",
        "bug",
        user_id=None,
    )

    assert len(fake.calls) == 1, "propose_description debe llamar al LLM exactamente una vez"
    assert "1098765432" not in fake.all_sent_text, (
        "La cédula real no debe llegar al LLM (PIIGuard debe haberla enmascarado)"
    )
    assert "[DOC_1]" in fake.all_sent_text, (
        "El LLM debe recibir el token [DOC_1] en lugar de la cédula real"
    )


@pytest.mark.asyncio
async def test_propose_description_masks_multiple_docs(monkeypatch):
    """Varias cédulas distintas generan tokens separados: [DOC_1], [DOC_2]."""
    fake = FakeProvider(response='{"bug_behavior": "x", "what_to_test": "y", "expected_result": "z", "fix": ""}')
    monkeypatch.setattr(factory_module, "get_provider", lambda: fake)

    svc = ContextService(repo=MagicMock())

    await svc.propose_description(
        "Afiliado con CC 1098765432 y su cónyuge CC 987654321 presentan el problema descrito en el reporte.",
        "bug",
        user_id=None,
    )

    sent = fake.all_sent_text
    assert "1098765432" not in sent
    assert "987654321" not in sent
    assert "[DOC_1]" in sent
    assert "[DOC_2]" in sent
