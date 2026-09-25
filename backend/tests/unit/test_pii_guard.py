import pytest

from app.llm.pii_guard import PIIDetectedError, PIIGuard


@pytest.fixture()
def guard() -> PIIGuard:
    return PIIGuard()


# ── detección ────────────────────────────────────────────────────────────────


def test_detects_document_number(guard: PIIGuard) -> None:
    matches = guard.check("El afiliado 12345678 tiene contrato activo")
    names = [m.pattern_name for m in matches]
    assert "document_number" in names


def test_detects_email(guard: PIIGuard) -> None:
    matches = guard.check("Contactar a juan.perez@empresa.com.co para confirmar")
    names = [m.pattern_name for m in matches]
    assert "email" in names


def test_detects_colombian_mobile(guard: PIIGuard) -> None:
    matches = guard.check("Llamar al 3001234567 antes de la novedad")
    names = [m.pattern_name for m in matches]
    assert "phone" in names


def test_clean_requirement_text_passes(guard: PIIGuard) -> None:
    text = "Validar que el sistema rechace la exclusión cuando la fecha de efecto es anterior"
    assert guard.check(text) == []


def test_column_names_pass_guard(guard: PIIGuard) -> None:
    column_names = "cedula, nombre_completo, contrato, fecha_inicio_ips, rol_afiliado"
    assert guard.check(column_names) == []


# ── assert_clean ─────────────────────────────────────────────────────────────


def test_assert_clean_raises_on_document_number(guard: PIIGuard) -> None:
    with pytest.raises(PIIDetectedError) as exc_info:
        guard.assert_clean("El afiliado 98765432 solicita exclusión")
    assert "document_number" in exc_info.value.matches[0].pattern_name


def test_assert_clean_raises_on_email(guard: PIIGuard) -> None:
    with pytest.raises(PIIDetectedError):
        guard.assert_clean("Correo: ana@example.com")


def test_assert_clean_passes_on_clean_text(guard: PIIGuard) -> None:
    guard.assert_clean("Verificar que el sistema muestre el mensaje de validación")


# ── mask ──────────────────────────────────────────────────────────────────────


def test_mask_removes_document_number(guard: PIIGuard) -> None:
    masked, count = guard.mask("CC: 12345678 del afiliado")
    assert "12345678" not in masked
    assert "[DOC_1]" in masked
    assert count >= 1


def test_mask_removes_email(guard: PIIGuard) -> None:
    masked, count = guard.mask("Correo test@example.com registrado")
    assert "test@example.com" not in masked
    assert count >= 1


def test_mask_is_sequential_and_covers_all_types(guard: PIIGuard) -> None:
    text = "CC 87654321 celular 3009876543 correo x@y.co"
    masked, count = guard.mask(text)
    assert "87654321" not in masked
    assert "3009876543" not in masked
    assert "x@y.co" not in masked
    assert count >= 3
    assert "[DOC_1]" in masked
    assert "[DOC_2]" in masked
