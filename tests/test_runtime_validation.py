import copy
import pytest

from hashoej_document_builder.core.validation import (
    decode_field_option_tokens,
    decode_option_token,
    get_field_display_label,
    get_initial_repeater_row,
    get_initial_values,
    parse_form_data,
    sanitize_step_input,
    validate_all_steps_values,
    validate_field_value,
    validate_step_values,
)


def test_get_initial_values_deepcopy_isolation() -> None:
    form_def = {
        "steps": [
            {
                "id": "step1",
                "title": "Trin 1",
                "fields": [
                    {"id": "name", "type": "text", "label": "Navn", "default": "Kasserer"},
                    {
                        "id": "tasks",
                        "type": "repeater",
                        "label": "Opgaver",
                        "default": [{"title": "Opgave 1"}],
                    },
                ],
            }
        ]
    }

    initial_1 = get_initial_values(form_def)
    initial_2 = get_initial_values(form_def)

    # Mutate initial_1
    initial_1["tasks"][0]["title"] = "Mutated Title"
    initial_1["tasks"].append({"title": "Opgave 2"})

    # Assert form_def and initial_2 are untouched
    assert form_def["steps"][0]["fields"][1]["default"] == [{"title": "Opgave 1"}]
    assert initial_2["tasks"] == [{"title": "Opgave 1"}]


def test_get_initial_repeater_row_child_defaults() -> None:
    rep_def = {
        "id": "tasks",
        "type": "repeater",
        "label": "Opgaver",
        "fields": [
            {"id": "title", "type": "text", "label": "Titel", "default": "Standardopgave"},
            {"id": "hours", "type": "number", "label": "Timer", "default": 5},
            {"id": "is_urgent", "type": "checkbox", "label": "Haster"},
            {"id": "tags", "type": "multiselect", "label": "Mærker", "options": ["A", "B"]},
            {"id": "notes", "type": "text", "label": "Noter"},
            {"id": "info_block", "type": "info", "text": "Hjælpetekst"},
        ],
    }

    row = get_initial_repeater_row(rep_def)
    assert row["title"] == "Standardopgave"
    assert row["hours"] == 5
    assert row["is_urgent"] is False
    assert row["tags"] == []
    assert row["notes"] == ""
    assert "info_block" not in row


def test_sanitize_step_input_preserves_explicit_empty_controls() -> None:
    step_def = {
        "id": "step1",
        "title": "Trin 1",
        "fields": [
            {"id": "role_name", "type": "text", "label": "Rollenavn"},
            {"id": "is_active", "type": "checkbox", "label": "Aktiv"},
            {"id": "sports", "type": "multiselect", "label": "Sport", "options": ["f", "g"]},
            {
                "id": "tasks",
                "type": "repeater",
                "label": "Opgaver",
                "fields": [
                    {"id": "title", "type": "text", "label": "Titel"},
                    {"id": "urgent", "type": "checkbox", "label": "Haster"},
                    {"id": "child_tags", "type": "multiselect", "label": "Tags", "options": ["1", "2"]},
                ],
            },
        ],
    }

    # Browser POST omitted unchecked checkbox and unselected multiselect
    raw_submitted = {
        "role_name": "Formand",
        # is_active omitted
        # sports omitted
        "tasks": [
            {
                "title": "Budget",
                # urgent omitted
                # child_tags omitted
            }
        ],
    }

    sanitized = sanitize_step_input(step_def, raw_submitted)

    assert sanitized["role_name"] == "Formand"
    assert sanitized["is_active"] is False
    assert sanitized["sports"] == []
    assert sanitized["tasks"] == [{"title": "Budget", "urgent": False, "child_tags": []}]


def test_sanitize_step_input_drops_unknown_fields_and_unapproved_children() -> None:
    step_def = {
        "id": "step1",
        "title": "Trin 1",
        "fields": [
            {"id": "role_name", "type": "text", "label": "Rollenavn"},
            {
                "id": "tasks",
                "type": "repeater",
                "label": "Opgaver",
                "fields": [
                    {"id": "title", "type": "text", "label": "Titel"},
                ],
            },
        ],
    }

    raw_submitted = {
        "role_name": "Formand",
        "action": "next",
        "admin": True,
        "__internal": "attack",
        "tasks": [
            {
                "title": "Budget",
                "unknown_child": "injected",
                "admin_role": True,
            }
        ],
    }

    sanitized = sanitize_step_input(step_def, raw_submitted)

    assert sanitized == {
        "role_name": "Formand",
        "tasks": [{"title": "Budget"}],
    }
    assert "action" not in sanitized
    assert "admin" not in sanitized
    assert "__internal" not in sanitized


def test_option_token_roundtrip_scalar_types() -> None:
    field_def = {
        "id": "mixed_options",
        "type": "select",
        "label": "Blandede valg",
        "options": [
            {"value": 1, "label": "Heltal 1"},
            {"value": "1", "label": "Streng 1"},
            {"value": True, "label": "Boolsk Sand"},
            {"value": False, "label": "Boolsk Falsk"},
        ],
    }

    # Test decoding token opt_0 -> 1 (int)
    decoded_0 = decode_option_token(field_def, "opt_0")
    assert decoded_0 == 1
    assert isinstance(decoded_0, int) and not isinstance(decoded_0, bool)

    # Test decoding token opt_1 -> "1" (str)
    decoded_1 = decode_option_token(field_def, "opt_1")
    assert decoded_1 == "1"
    assert isinstance(decoded_1, str)

    # Test decoding token opt_2 -> True (bool)
    decoded_2 = decode_option_token(field_def, "opt_2")
    assert decoded_2 is True
    assert isinstance(decoded_2, bool)

    # Test decoding token opt_3 -> False (bool)
    decoded_3 = decode_option_token(field_def, "opt_3")
    assert decoded_3 is False
    assert isinstance(decoded_3, bool)

    # Already typed values remain distinguishable
    assert decode_option_token(field_def, 1) == 1
    assert isinstance(decode_option_token(field_def, 1), int) and not isinstance(decode_option_token(field_def, 1), bool)
    assert decode_option_token(field_def, "1") == "1"
    assert isinstance(decode_option_token(field_def, "1"), str)
    assert decode_option_token(field_def, True) is True
    assert decode_option_token(field_def, False) is False

    # Raw string "1" for a select with only integer 1 must NOT silently become integer 1
    int_only_field = {
        "id": "int_only",
        "type": "select",
        "label": "Kun tal",
        "options": [{"value": 1, "label": "Et"}],
    }
    raw_str_decoded = decode_option_token(int_only_field, "1")
    assert raw_str_decoded == "1"
    assert isinstance(raw_str_decoded, str)  # not coerced to int 1


def test_parse_form_data_with_row_marker() -> None:
    raw = {
        "role_name": "Formand",
        "tasks.0._row": "1",
        "tasks.0.title": "Opgave 1",
        "tasks.1._row": "1",  # row with no other inputs
    }
    parsed = parse_form_data(raw)
    assert parsed["role_name"] == "Formand"
    assert len(parsed["tasks"]) == 2
    assert parsed["tasks"][0] == {"title": "Opgave 1"}
    assert parsed["tasks"][1] == {}
    assert "_row" not in parsed["tasks"][0]


def test_harden_scalar_form_coercion() -> None:
    # Scalar text with compound dict or list
    text_def = {"id": "text_f", "type": "text", "label": "Tekst"}
    val, err = validate_field_value(text_def, ["item1", "item2"])
    assert err == "Ugyldigt dataformat."

    val, err = validate_field_value(text_def, {"key": "value"})
    assert err == "Ugyldigt dataformat."

    # Number with compound list
    num_def = {"id": "num_f", "type": "number", "label": "Nummer"}
    val, err = validate_field_value(num_def, [1, 2])
    assert err == "Ugyldigt dataformat."

    # Select with unhashable compound dict
    select_def = {
        "id": "select_f",
        "type": "select",
        "label": "Valg",
        "options": [{"value": "a", "label": "Valg A"}],
    }
    val, err = validate_field_value(select_def, {"unhashable": "dict"})
    assert err == "Ugyldigt dataformat."

    # Checkbox with compound list
    chk_def = {"id": "chk_f", "type": "checkbox", "label": "Tjek"}
    val, err = validate_field_value(chk_def, [True, False])
    assert err == "Ugyldigt dataformat."


def test_required_and_optional_repeaters() -> None:
    req_repeater_no_min = {
        "id": "tasks",
        "type": "repeater",
        "label": "Opgaver",
        "required": True,
        "fields": [{"id": "title", "type": "text", "label": "Titel", "required": True}],
    }

    # Empty rows on required repeater must fail
    val, err = validate_field_value(req_repeater_no_min, [])
    assert err == "Tilføj mindst 1 række."

    # Valid row passes
    val, err = validate_field_value(req_repeater_no_min, [{"title": "Opgave"}])
    assert err is None
    assert val == [{"title": "Opgave"}]

    # Optional repeater
    opt_repeater = {
        "id": "tasks",
        "type": "repeater",
        "label": "Opgaver",
        "required": False,
        "fields": [{"id": "title", "type": "text", "label": "Titel", "required": True}],
    }
    val, err = validate_field_value(opt_repeater, [])
    assert err is None
    assert val == []

    # Repeater with min_items: 2
    min2_repeater = {
        "id": "tasks",
        "type": "repeater",
        "label": "Opgaver",
        "min_items": 2,
        "fields": [{"id": "title", "type": "text", "label": "Titel", "required": True}],
    }
    val, err = validate_field_value(min2_repeater, [{"title": "Opgave 1"}])
    assert err == "Tilføj mindst 2 rækker."


def test_validate_step_values_repeater_min_items_regression() -> None:
    """Direct regression tests ensuring validate_step_values never raises NameError for min_items."""
    # 1. Optional repeater with min_items: 2 and 1 row
    step_opt = {
        "id": "step_opt",
        "title": "Valgfri liste",
        "fields": [
            {
                "id": "tasks",
                "type": "repeater",
                "label": "Opgaver",
                "required": False,
                "min_items": 2,
                "fields": [{"id": "title", "type": "text", "label": "Titel", "required": True}],
            }
        ],
    }
    res_opt = validate_step_values(step_opt, {"tasks": [{"title": "Opgave 1"}]}, {})
    assert res_opt.is_valid is False
    assert res_opt.errors["tasks"] == "Tilføj mindst 2 rækker."

    # 2. Required repeater with min_items: 2 and 1 row
    step_req = {
        "id": "step_req",
        "title": "Påkrævet liste",
        "fields": [
            {
                "id": "tasks",
                "type": "repeater",
                "label": "Opgaver",
                "required": True,
                "min_items": 2,
                "fields": [{"id": "title", "type": "text", "label": "Titel", "required": True}],
            }
        ],
    }
    res_req = validate_step_values(step_req, {"tasks": [{"title": "Opgave 1"}]}, {})
    assert res_req.is_valid is False
    assert res_req.errors["tasks"] == "Tilføj mindst 2 rækker."


def test_get_field_display_label_resolution() -> None:
    select_def = {
        "id": "role_level",
        "type": "select",
        "label": "Niveau",
        "options": [
            {"value": "board", "label": "Hovedbestyrelse"},
            {"value": "committee", "label": "Underudvalg"},
        ],
    }

    assert get_field_display_label(select_def, "board") == "Hovedbestyrelse"
    assert get_field_display_label(select_def, "committee") == "Underudvalg"
    assert get_field_display_label(select_def, "unknown") == "unknown"

    multi_def = {
        "id": "sports",
        "type": "multiselect",
        "label": "Sportsgrene",
        "options": [
            {"value": "f", "label": "Fodbold"},
            {"value": "g", "label": "Gymnastik"},
        ],
    }
    assert get_field_display_label(multi_def, ["f", "g"]) == ["Fodbold", "Gymnastik"]
