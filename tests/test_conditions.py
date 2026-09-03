import pytest

from hashoej_document_builder.core.conditions import evaluate_condition, is_field_active
from hashoej_document_builder.core.validation import (
    normalize_step_values_for_conditions,
    validate_step_values,
)


def test_evaluate_condition_empty_or_none() -> None:
    assert evaluate_condition(None, {}) is True
    assert evaluate_condition({}, {}) is True


def test_operator_equals() -> None:
    cond = {"field": "role_level", "equals": "committee"}

    assert evaluate_condition(cond, {"role_level": "committee"}) is True
    assert evaluate_condition(cond, {"role_level": "board"}) is False
    assert evaluate_condition(cond, {}) is False


def test_operator_not_equals() -> None:
    cond = {"field": "role_level", "not_equals": "board"}

    assert evaluate_condition(cond, {"role_level": "committee"}) is True
    assert evaluate_condition(cond, {"role_level": "board"}) is False
    assert evaluate_condition(cond, {}) is True


def test_operator_in() -> None:
    cond = {"field": "role_level", "in": ["board", "committee"]}

    assert evaluate_condition(cond, {"role_level": "board"}) is True
    assert evaluate_condition(cond, {"role_level": "committee"}) is True
    assert evaluate_condition(cond, {"role_level": "other"}) is False
    assert evaluate_condition(cond, {}) is False


def test_operator_not_in() -> None:
    cond = {"field": "role_level", "not_in": ["board"]}

    assert evaluate_condition(cond, {"role_level": "committee"}) is True
    assert evaluate_condition(cond, {"role_level": "board"}) is False
    assert evaluate_condition(cond, {}) is True


def test_typed_checkbox_show_when_evaluation() -> None:
    step_def = {
        "id": "step1",
        "title": "Trin 1",
        "fields": [
            {"id": "has_supplier", "type": "checkbox", "label": "Har leverandør?"},
            {
                "id": "supplier_name",
                "type": "text",
                "label": "Leverandørnavn",
                "required": True,
                "show_when": {"field": "has_supplier", "equals": True},
            },
        ],
    }

    # Browser submitted "on" or "true" string
    normalized_checked = normalize_step_values_for_conditions(step_def, {"has_supplier": "true"})
    assert normalized_checked["has_supplier"] is True
    assert is_field_active(step_def["fields"][1], normalized_checked) is True

    # Browser submitted unchecked (missing / false)
    normalized_unchecked = normalize_step_values_for_conditions(step_def, {})
    assert normalized_unchecked["has_supplier"] is False
    assert is_field_active(step_def["fields"][1], normalized_unchecked) is False


def test_typed_number_and_boolean_option_values() -> None:
    step_def = {
        "id": "step1",
        "title": "Trin 1",
        "fields": [
            {
                "id": "tier",
                "type": "select",
                "label": "Niveau",
                "options": [{"value": 1, "label": "Tier 1"}, {"value": 2, "label": "Tier 2"}],
            },
            {
                "id": "tier2_field",
                "type": "text",
                "label": "Tier 2 Detalje",
                "show_when": {"field": "tier", "equals": 2},
            },
        ],
    }

    # Browser submits option token "opt_1" (corresponding to integer 2)
    normalized = normalize_step_values_for_conditions(step_def, {"tier": "opt_1"})
    assert normalized["tier"] == 2
    assert is_field_active(step_def["fields"][1], normalized) is True

    # Option token "opt_0" (corresponding to integer 1)
    normalized_1 = normalize_step_values_for_conditions(step_def, {"tier": "opt_0"})
    assert normalized_1["tier"] == 1
    assert is_field_active(step_def["fields"][1], normalized_1) is False
