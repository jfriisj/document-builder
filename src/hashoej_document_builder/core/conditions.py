"""Generic runtime condition evaluation for template fields."""

from __future__ import annotations

from typing import Any


def _matches_value(actual: Any, expected: Any) -> bool:
    """Check if actual matches expected, enforcing boolean/integer type distinction."""
    if type(actual) is bool or type(expected) is bool:
        return type(actual) is type(expected) and actual == expected
    return actual == expected


def evaluate_condition(condition: dict[str, Any] | None, values: dict[str, Any]) -> bool:
    """Evaluate a field's show_when condition against current session values.

    Supported operators:
      - equals: True if values[field] == value (with strict boolean type matching)
      - not_equals: True if values[field] != value
      - in: True if values[field] is in value_list
      - not_in: True if values[field] is not in value_list

    If condition is None or empty, returns True.
    """
    if not condition:
        return True

    target_field = condition.get("field")
    if not target_field:
        return True

    current_val = values.get(target_field)

    if "equals" in condition:
        expected = condition["equals"]
        return _matches_value(current_val, expected)

    if "not_equals" in condition:
        expected = condition["not_equals"]
        return not _matches_value(current_val, expected)

    if "in" in condition:
        expected_list = condition["in"]
        if not isinstance(expected_list, (list, tuple, set)):
            return False
        return any(_matches_value(current_val, item) for item in expected_list)

    if "not_in" in condition:
        expected_list = condition["not_in"]
        if not isinstance(expected_list, (list, tuple, set)):
            return True
        return not any(_matches_value(current_val, item) for item in expected_list)

    return True


def is_field_active(field_def: dict[str, Any], values: dict[str, Any]) -> bool:
    """Check if a field is active given the current session values."""
    if "show_when" not in field_def:
        return True
    return evaluate_condition(field_def["show_when"], values)
