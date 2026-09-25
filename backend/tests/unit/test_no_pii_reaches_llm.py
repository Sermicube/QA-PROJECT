"""
Tests de privacidad — RF-RNF-01 / §9 de SPEC.md

El test completo `test_no_pii_reaches_llm` (flujo con base de usuarios real y
FakeProvider espía) se completará en la Fase 2 (módulo testdata). Aquí se
verifica que la guardia de privacidad funciona correctamente de forma aislada
y que el patrón de uso es correcto: solo nombres de columna y condiciones
llegan al LLM, nunca valores de afiliados.
"""

import pytest

from app.llm.fake_provider import FakeProvider
from app.llm.pii_guard import PIIDetectedError, PIIGuard
from app.llm.provider import Message

# Valores sintéticos que simulan datos de una base de afiliados
_SYNTHETIC_PII = [
    ("document_number", "12345678"),
    ("document_number", "987654321"),
    ("email", "afiliado@salud.gov.co"),
    ("phone", "3159876543"),
]

# Lo que sí se puede enviar al LLM (RF-22, RF-23)
_SAFE_TO_SEND = [
    "cedula, nombre_completo, contrato, fecha_inicio_ips",
    '{"field": "affiliate_role", "op": "eq", "value": "beneficiario"}',
    "Validar que el sistema rechace la novedad cuando la fecha de efecto es anterior",
]


# ── guardia bloquea PII ───────────────────────────────────────────────────────


@pytest.mark.parametrize("pattern_name,value", _SYNTHETIC_PII)
def test_pii_guard_blocks_affiliate_data(pattern_name: str, value: str) -> None:
    guard = PIIGuard()
    with pytest.raises(PIIDetectedError) as exc_info:
        guard.assert_clean(f"dato del afiliado: {value}")
    detected_types = {m.pattern_name for m in exc_info.value.matches}
    assert pattern_name in detected_types


# ── lo seguro pasa la guardia ─────────────────────────────────────────────────


@pytest.mark.parametrize("safe_text", _SAFE_TO_SEND)
def test_safe_content_passes_pii_guard(safe_text: str) -> None:
    guard = PIIGuard()
    guard.assert_clean(safe_text)  # no debe lanzar


# ── FakeProvider espía no recibe PII ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_fake_provider_spy_detects_if_pii_sent() -> None:
    """
    Simula el patrón correcto: se envía solo columnas y condiciones,
    nunca los valores de la fila del afiliado.
    """
    guard = PIIGuard()
    provider = FakeProvider(response="{}")

    safe_column_names = "cedula, nombre_completo, contrato, fecha_inicio_ips"
    guard.assert_clean(safe_column_names)  # la guardia valida antes de enviar

    await provider.complete(
        system="Propone el mapeo de columnas al dominio",
        messages=[Message(role="user", content=safe_column_names)],
        max_tokens=256,
    )

    # El texto enviado no contiene PII de la fila
    for _, pii_value in _SYNTHETIC_PII:
        assert pii_value not in provider.all_sent_text


@pytest.mark.asyncio
async def test_pii_in_content_would_be_blocked_before_send() -> None:
    """
    Si por error el servicio intentara enviar un valor de afiliado,
    la guardia lo detiene antes de llamar al provider.
    """
    guard = PIIGuard()
    provider = FakeProvider()

    pii_text = "El afiliado con cédula 12345678 solicita exclusión"

    with pytest.raises(PIIDetectedError):
        guard.assert_clean(pii_text)
        # Esta línea nunca se alcanza
        await provider.complete("sys", [Message(role="user", content=pii_text)], max_tokens=100)

    assert len(provider.calls) == 0  # el provider nunca fue llamado


# ── texto de requerimiento se enmascara antes de enviar ──────────────────────


def test_requirement_document_with_examples_is_masked() -> None:
    """
    Los documentos de requerimiento pueden incluir ejemplos con datos reales.
    Se enmascaran (no se bloquean) antes de enviar al LLM. (RF-10, §6.2)
    """
    guard = PIIGuard()
    original = (
        "Cuando la cédula del afiliado es 98765432 y su correo es ana@clinica.com "
        "el sistema debe rechazar la novedad de exclusión."
    )
    masked, count = guard.mask(original)

    assert "98765432" not in masked
    assert "ana@clinica.com" not in masked
    assert count >= 2
    assert "[DOC_" in masked

    # El texto enmascarado sí pasa la guardia
    guard.assert_clean(masked)
