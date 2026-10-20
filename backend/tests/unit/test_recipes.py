"""Unit tests for recipes seed data — RF-01c, RF-20b."""

import pytest

from app.recipes import seed


def test_all_eight_recipes_defined() -> None:
    codes = {r["code"] for r in seed.RECIPES}
    expected = {
        "bug_simple", "bug_before_after", "bug_negative_control",
        "brecha_date_rule", "service_soap_xml", "service_rest_json",
        "file_batch", "client_cases",
    }
    assert codes == expected


def test_all_stages_present_in_every_recipe() -> None:
    for recipe in seed.RECIPES:
        missing = set(seed.ALL_STAGES) - set(recipe["stages"].keys())
        assert missing == set(), f"Receta '{recipe['code']}' sin etapas: {missing}"


def test_stage_modes_are_valid() -> None:
    valid = {"required", "optional", "not_applicable"}
    for recipe in seed.RECIPES:
        for stage, mode in recipe["stages"].items():
            assert mode in valid, f"Receta '{recipe['code']}' etapa '{stage}': modo inválido '{mode}'"


def test_bug_recipes_include_format_as_required() -> None:
    bug_recipes = [r for r in seed.RECIPES if r["code"] in (
        "bug_simple", "bug_before_after", "bug_negative_control"
    )]
    for recipe in bug_recipes:
        assert recipe["stages"]["format"] == "required", (
            f"Receta '{recipe['code']}' debe tener format=required"
        )


def test_file_batch_includes_format_as_required() -> None:
    recipe = next(r for r in seed.RECIPES if r["code"] == "file_batch")
    assert recipe["stages"]["format"] == "required"


def test_file_batch_default_pattern_is_one_case() -> None:
    recipe = next(r for r in seed.RECIPES if r["code"] == "file_batch")
    assert recipe["suggested_case_pattern"] == "one_case"


def test_service_rest_json_analysis_is_required() -> None:
    recipe = next(r for r in seed.RECIPES if r["code"] == "service_rest_json")
    assert recipe["stages"]["analysis"] == "required"


def test_service_rest_json_default_origin_is_manual_search() -> None:
    recipe = next(r for r in seed.RECIPES if r["code"] == "service_rest_json")
    assert recipe["default_data_origin"] == "manual_search"


def test_service_rest_json_data_request_and_assignment_are_optional() -> None:
    recipe = next(r for r in seed.RECIPES if r["code"] == "service_rest_json")
    assert recipe["stages"]["data_request"] == "optional"
    assert recipe["stages"]["assignment"] == "optional"


def test_service_soap_xml_all_stages_required() -> None:
    recipe = next(r for r in seed.RECIPES if r["code"] == "service_soap_xml")
    for stage, mode in recipe["stages"].items():
        assert mode == "required", f"soap_xml: etapa '{stage}' debería ser required, es '{mode}'"


def test_five_inconclusive_reasons_defined() -> None:
    codes = {r["code"] for r in seed.INCONCLUSIVE_REASONS}
    expected = {
        "data_condition_not_met", "date_out_of_validity", "data_already_corrected",
        "other_validation_noise", "other",
    }
    assert codes == expected


def test_five_case_styles_defined() -> None:
    codes = {s["code"] for s in seed.CASE_STYLES}
    expected = {"short", "validate_that", "action_validations", "consult_service", "full_sheet"}
    assert codes == expected


def test_nine_case_patterns_defined() -> None:
    codes = {p["code"] for p in seed.CASE_PATTERNS}
    expected = {
        "one_case", "before_after", "negative_control", "boundary",
        "threshold_control_oos", "by_scenario", "matrix_by_role",
        "client_cases", "logic_monitoring",
    }
    assert codes == expected


def test_all_builtin_recipes_are_marked_builtin() -> None:
    for recipe in seed.RECIPES:
        assert recipe["is_builtin"] is True
