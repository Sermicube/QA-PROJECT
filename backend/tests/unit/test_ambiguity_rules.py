"""Tests para app.context.domain.ambiguity_rules (RF-13)."""
import pytest
from app.context.domain.ambiguity_rules import scan_text, scan_sources, AmbiguityFinding


class TestBoundaryUndefined:
    def test_mayor_que_detectado(self):
        findings = scan_text("Si el valor es mayor que 100 se rechaza.", "sec")
        types = [f.type for f in findings]
        assert "boundary_undefined" in types

    def test_menor_que_detectado(self):
        findings = scan_text("Cuando sea menor que la fecha de efecto.", "sec")
        assert any(f.type == "boundary_undefined" for f in findings)

    def test_superior_que_detectado(self):
        findings = scan_text("Monto superior que el límite permitido.", "sec")
        assert any(f.type == "boundary_undefined" for f in findings)

    def test_inferior_que_detectado(self):
        findings = scan_text("Inferior que el mínimo requerido.", "sec")
        assert any(f.type == "boundary_undefined" for f in findings)

    def test_sin_comparacion_no_detecta(self):
        findings = scan_text("El sistema registra la novedad correctamente.", "sec")
        assert not any(f.type == "boundary_undefined" for f in findings)

    def test_fragment_contiene_contexto(self):
        text = "Si el monto es mayor que el límite se rechaza la solicitud."
        findings = scan_text(text, "test")
        boundary = [f for f in findings if f.type == "boundary_undefined"]
        assert boundary
        assert "mayor" in boundary[0].fragment.lower()

    def test_location_propagada(self):
        findings = scan_text("Valor mayor que 0.", "seccion_2")
        assert findings[0].location == "seccion_2"

    def test_question_no_vacia(self):
        findings = scan_text("Fecha mayor que la de contrato.", "x")
        assert findings[0].question


class TestImplicitUnit:
    def test_dias_sin_tipo_detectado(self):
        findings = scan_text("La solicitud se procesa en 3 días.", "sec")
        assert any(f.type == "implicit_unit" for f in findings)

    def test_dias_habiles_no_detectado(self):
        findings = scan_text("Plazo de 5 días hábiles.", "sec")
        assert not any(f.type == "implicit_unit" for f in findings)

    def test_dias_calendario_no_detectado(self):
        findings = scan_text("Plazo de 5 días calendario.", "sec")
        assert not any(f.type == "implicit_unit" for f in findings)

    def test_dias_naturales_no_detectado(self):
        findings = scan_text("Plazo de 10 días naturales.", "sec")
        assert not any(f.type == "implicit_unit" for f in findings)

    def test_question_menciona_habiles(self):
        findings = scan_text("En 7 días el sistema envía aviso.", "sec")
        unit = [f for f in findings if f.type == "implicit_unit"]
        assert unit
        assert "hábiles" in unit[0].question.lower() or "habiles" in unit[0].question.lower()


class TestVagueTerm:
    def test_correctamente_detectado(self):
        findings = scan_text("El sistema procesa correctamente la novedad.", "sec")
        assert any(f.type == "vague_term" for f in findings)

    def test_adecuadamente_detectado(self):
        findings = scan_text("Se genera adecuadamente el documento.", "sec")
        assert any(f.type == "vague_term" for f in findings)

    def test_exitosamente_detectado(self):
        findings = scan_text("Se guarda de forma exitosa.", "sec")
        assert any(f.type == "vague_term" for f in findings)

    def test_si_aplica_detectado(self):
        findings = scan_text("El campo se completa si aplica.", "sec")
        assert any(f.type == "vague_term" for f in findings)

    def test_texto_concreto_no_detecta_vago(self):
        findings = scan_text("Se muestra el mensaje 'Contrato terminado'.", "sec")
        assert not any(f.type == "vague_term" for f in findings)


class TestNoDuplicados:
    def test_mismo_fragmento_no_duplicado(self):
        text = "Valor mayor que el mínimo. Otro mayor que el máximo."
        findings = scan_text(text, "sec")
        types = [f.type for f in findings]
        # Pueden aparecer varias veces pero con fragmentos distintos (no el mismo key)
        keys = [(f.type, f.fragment[:60]) for f in findings]
        assert len(keys) == len(set(keys))


class TestScanSources:
    def test_multiples_fuentes(self):
        sources = [
            {"kind": "requirement_document", "text": "Aplica si el valor es mayor que 100.", "sections": []},
            {"kind": "analyst_description", "text": "Proceso en 5 días.", "sections": []},
        ]
        findings = scan_sources(sources)
        types = {f.type for f in findings}
        assert "boundary_undefined" in types
        assert "implicit_unit" in types

    def test_fuente_con_secciones(self):
        sources = [
            {
                "kind": "req",
                "text": "",
                "sections": [
                    {"title": "Reglas", "content": "Monto mayor que el límite."},
                    {"title": "Proceso", "content": "En 3 días hábiles."},
                ],
            }
        ]
        findings = scan_sources(sources)
        assert any(f.type == "boundary_undefined" for f in findings)
        assert not any(f.type == "implicit_unit" for f in findings)

    def test_fuente_vacia_sin_hallazgos(self):
        sources = [{"kind": "incident_report", "text": "", "sections": []}]
        findings = scan_sources(sources)
        assert findings == []
