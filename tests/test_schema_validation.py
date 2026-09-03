import pytest

from hashoej_document_builder.core.errors import TemplateValidationError
from hashoej_document_builder.core.schema import validate_template_definition


def sample_valid_template() -> dict:
    return {
        "id": "hif-01-role",
        "version": 1,
        "enabled": True,
        "title": "Rollebeskrivelse",
        "category": "Organisation",
        "description": "Beskriv ansvar og opgaver for en rolle i Hashøj IF.",
        "steps": [
            {
                "id": "basic",
                "title": "Grundoplysninger",
                "description": "Indtast basale rolleoplysninger",
                "fields": [
                    {
                        "id": "role_name",
                        "type": "text",
                        "label": "Hvad hedder rollen?",
                        "required": True,
                        "min_length": 2,
                        "max_length": 100,
                        "default": "Formand",
                    },
                    {
                        "id": "contact_email",
                        "type": "text",
                        "label": "Kontakt e-mail",
                        "format": "email",
                        "required": False,
                    },
                    {
                        "id": "estimated_hours",
                        "type": "number",
                        "label": "Forventet ugentligt timetal",
                        "min": 1,
                        "max": 40,
                        "default": 5,
                    },
                    {
                        "id": "role_level",
                        "type": "select",
                        "label": "Rolleniveau",
                        "options": [
                            {"value": "board", "label": "Bestyrelse"},
                            {"value": "committee", "label": "Udvalg"},
                        ],
                        "default": "board",
                    },
                    {
                        "id": "committee_name",
                        "type": "text",
                        "label": "Udvalgets navn",
                        "show_when": {
                            "field": "role_level",
                            "equals": "committee",
                        },
                    },
                ],
            },
            {
                "id": "tasks_and_privacy",
                "title": "Opgaver og samtykke",
                "fields": [
                    {
                        "id": "tasks",
                        "type": "repeater",
                        "label": "Rolleopgaver",
                        "min_items": 1,
                        "max_items": 10,
                        "fields": [
                            {"id": "task_title", "type": "text", "label": "Opgavetitel"},
                            {"id": "task_frequency", "type": "text", "label": "Hyppighed"},
                        ],
                    },
                    {
                        "id": "privacy_info",
                        "type": "info",
                        "variant": "privacy",
                        "text": "Oplysningerne gemmes ikke permanent og behandles kun til at generere dokumentet.",
                    },
                    {
                        "id": "privacy_ack",
                        "type": "checkbox",
                        "label": "Jeg forstår at data ikke gemmes permanent",
                        "purpose": "acknowledgement",
                        "required": True,
                        "default": False,
                    },
                    {
                        "id": "photo_consent",
                        "type": "checkbox",
                        "label": "Jeg giver samtykke til offentliggørelse af kontaktinfo",
                        "purpose": "consent",
                        "default": False,
                    },
                ],
            },
        ],
    }


def test_valid_template_definition_passes() -> None:
    data = sample_valid_template()
    validated = validate_template_definition(data)
    assert validated["id"] == "hif-01-role"
    assert validated["version"] == 1
    assert len(validated["steps"]) == 2
    assert len(validated["steps"][0]["fields"]) == 5
    assert len(validated["steps"][1]["fields"]) == 4


def test_non_dict_rejected() -> None:
    with pytest.raises(TemplateValidationError, match="must be a YAML dictionary"):
        validate_template_definition(["not", "a", "dict"])


@pytest.mark.parametrize(
    "field_name,invalid_value",
    [
        ("id", ""),
        ("id", "Invalid_ID"),
        ("id", "hif--01"),
        ("id", None),
        ("version", 0),
        ("version", -1),
        ("version", "1"),
        ("version", True),  # bool is subclass of int in Python
        ("enabled", "true"),
        ("enabled", 1),
        ("title", ""),
        ("title", "   "),
        ("category", ""),
        ("description", ""),
        ("steps", []),
        ("steps", "not a list"),
    ],
)
def test_invalid_top_level_metadata(field_name: str, invalid_value: object) -> None:
    data = sample_valid_template()
    data[field_name] = invalid_value
    with pytest.raises(TemplateValidationError):
        validate_template_definition(data)


@pytest.mark.parametrize(
    "invalid_step_id",
    ["", "Step 1", "STEP_1", "step__1", None],
)
def test_invalid_step_id(invalid_step_id: object) -> None:
    data = sample_valid_template()
    data["steps"][0]["id"] = invalid_step_id
    with pytest.raises(TemplateValidationError):
        validate_template_definition(data)


def test_duplicate_step_id_rejected() -> None:
    data = sample_valid_template()
    data["steps"][1]["id"] = data["steps"][0]["id"]
    with pytest.raises(TemplateValidationError, match="Duplicate step id"):
        validate_template_definition(data)


def test_step_without_title_or_fields() -> None:
    data = sample_valid_template()
    data["steps"][0]["title"] = ""
    with pytest.raises(TemplateValidationError):
        validate_template_definition(data)

    data2 = sample_valid_template()
    data2["steps"][0]["fields"] = []
    with pytest.raises(TemplateValidationError):
        validate_template_definition(data2)


@pytest.mark.parametrize(
    "invalid_field_id",
    ["RoleName", "role-name", "role name", "_role", "role_", "role__name", "", None],
)
def test_field_id_must_be_snake_case(invalid_field_id: object) -> None:
    data = sample_valid_template()
    data["steps"][0]["fields"][0]["id"] = invalid_field_id
    with pytest.raises(TemplateValidationError):
        validate_template_definition(data)


def test_duplicate_top_level_field_ids_rejected() -> None:
    data = sample_valid_template()
    # Put duplicate field id in second step
    data["steps"][1]["fields"][0]["id"] = "role_name"
    with pytest.raises(TemplateValidationError, match="Duplicate top-level field id"):
        validate_template_definition(data)


def test_unsupported_field_type_rejected() -> None:
    data = sample_valid_template()
    data["steps"][0]["fields"][0]["type"] = "unsupported_widget"
    with pytest.raises(TemplateValidationError, match="Unsupported field type"):
        validate_template_definition(data)


def test_interactive_field_requires_label() -> None:
    data = sample_valid_template()
    data["steps"][0]["fields"][0]["label"] = ""
    with pytest.raises(TemplateValidationError, match="must have a non-empty 'label'"):
        validate_template_definition(data)


def test_info_field_requires_text() -> None:
    data = sample_valid_template()
    info_field = data["steps"][1]["fields"][1]
    info_field["text"] = ""
    with pytest.raises(TemplateValidationError, match="must have non-empty 'text'"):
        validate_template_definition(data)


def test_info_field_variant_validation() -> None:
    data = sample_valid_template()
    info_field = data["steps"][1]["fields"][1]
    info_field["variant"] = "invalid_variant"
    with pytest.raises(TemplateValidationError, match="Unsupported variant"):
        validate_template_definition(data)


def test_info_field_cannot_have_default() -> None:
    data = sample_valid_template()
    info_field = data["steps"][1]["fields"][1]
    info_field["default"] = "info default"
    with pytest.raises(TemplateValidationError, match="cannot have a 'default' value"):
        validate_template_definition(data)


@pytest.mark.parametrize("valid_fmt", ["email", "tel", "url"])
def test_supported_text_formats(valid_fmt: str) -> None:
    data = sample_valid_template()
    data["steps"][0]["fields"][0]["format"] = valid_fmt
    validated = validate_template_definition(data)
    assert validated["steps"][0]["fields"][0]["format"] == valid_fmt


@pytest.mark.parametrize("invalid_fmt", ["date", "ip", "custom", "numeric", "uri"])
def test_unsupported_text_formats_rejected(invalid_fmt: str) -> None:
    data = sample_valid_template()
    data["steps"][0]["fields"][0]["format"] = invalid_fmt
    with pytest.raises(TemplateValidationError, match="unsupported text format"):
        validate_template_definition(data)


def test_purpose_restricted_to_checkbox() -> None:
    data = sample_valid_template()

    # Valid checkbox purposes pass
    data["steps"][1]["fields"][2]["purpose"] = "acknowledgement"
    data["steps"][1]["fields"][3]["purpose"] = "consent"
    validated = validate_template_definition(data)
    assert validated["steps"][1]["fields"][2]["purpose"] == "acknowledgement"
    assert validated["steps"][1]["fields"][3]["purpose"] == "consent"

    # Purpose on info field is rejected
    data2 = sample_valid_template()
    data2["steps"][1]["fields"][1]["purpose"] = "acknowledgement"
    with pytest.raises(TemplateValidationError, match="'purpose' is only allowed on 'checkbox' fields"):
        validate_template_definition(data2)

    # Purpose on text field is rejected
    data3 = sample_valid_template()
    data3["steps"][0]["fields"][0]["purpose"] = "consent"
    with pytest.raises(TemplateValidationError, match="'purpose' is only allowed on 'checkbox' fields"):
        validate_template_definition(data3)

    # Unsupported purpose value is rejected
    data4 = sample_valid_template()
    data4["steps"][1]["fields"][2]["purpose"] = "marketing_tracking"
    with pytest.raises(TemplateValidationError, match="Unsupported purpose"):
        validate_template_definition(data4)


@pytest.mark.parametrize(
    "options_payload",
    [
        [],
        "not a list",
        [""],
        [{"value": "", "label": "Label"}],
        [{"value": "v1", "label": ""}],
        ["duplicate", "duplicate"],
        [{"value": "same", "label": "A"}, {"value": "same", "label": "B"}],
        [{"value": {"nested": "dict"}, "label": "Bad"}],
        [{"value": [1, 2], "label": "Bad List"}],
    ],
)
def test_invalid_options(options_payload: object) -> None:
    data = sample_valid_template()
    select_field = data["steps"][0]["fields"][3]
    select_field["options"] = options_payload
    with pytest.raises(TemplateValidationError):
        validate_template_definition(data)


def test_string_options_are_normalized() -> None:
    data = sample_valid_template()
    select_field = data["steps"][0]["fields"][3]
    select_field["options"] = ["Bestyrelse", "Udvalg"]
    select_field["default"] = "Bestyrelse"
    validated = validate_template_definition(data)
    opts = validated["steps"][0]["fields"][3]["options"]
    assert opts == [
        {"value": "Bestyrelse", "label": "Bestyrelse"},
        {"value": "Udvalg", "label": "Udvalg"},
    ]


def test_repeater_validation() -> None:
    data = sample_valid_template()
    repeater = data["steps"][1]["fields"][0]

    # No fields
    repeater["fields"] = []
    with pytest.raises(TemplateValidationError, match="must contain a non-empty 'fields' list"):
        validate_template_definition(data)

    # Nested repeater forbidden
    repeater["fields"] = [
        {"id": "sub_rep", "type": "repeater", "label": "Nested", "fields": [{"id": "sub", "type": "text", "label": "Sub"}]}
    ]
    with pytest.raises(TemplateValidationError, match="Nested repeater"):
        validate_template_definition(data)

    # Duplicate child field ID
    repeater["fields"] = [
        {"id": "task_id", "type": "text", "label": "Task 1"},
        {"id": "task_id", "type": "text", "label": "Task 2"},
    ]
    with pytest.raises(TemplateValidationError, match="Duplicate child field id"):
        validate_template_definition(data)


def test_repeater_child_field_show_when_rejected() -> None:
    data = sample_valid_template()
    repeater = data["steps"][1]["fields"][0]
    repeater["fields"] = [
        {"id": "task_title", "type": "text", "label": "Opgavetitel"},
        {
            "id": "task_frequency",
            "type": "text",
            "label": "Hyppighed",
            "show_when": {"field": "task_title", "equals": "Møder"},
        },
    ]
    with pytest.raises(TemplateValidationError, match="Conditional logic on repeater child fields is not supported in Milestone 2"):
        validate_template_definition(data)


def test_condition_validation_operators() -> None:
    data = sample_valid_template()
    cond_field = data["steps"][0]["fields"][4]

    # Reference unknown field
    cond_field["show_when"] = {"field": "non_existent_field", "equals": "yes"}
    with pytest.raises(TemplateValidationError, match="referencing unknown field"):
        validate_template_definition(data)

    # Reference self
    cond_field["show_when"] = {"field": "committee_name", "equals": "yes"}
    with pytest.raises(TemplateValidationError, match="cannot reference itself"):
        validate_template_definition(data)

    # Reference info field
    cond_field["show_when"] = {"field": "privacy_info", "equals": "yes"}
    with pytest.raises(TemplateValidationError, match="referencing info field"):
        validate_template_definition(data)

    # Multiple operators
    cond_field["show_when"] = {"field": "role_level", "equals": "committee", "not_equals": "board"}
    with pytest.raises(TemplateValidationError, match="contains multiple operators"):
        validate_template_definition(data)

    # Unsupported operator
    cond_field["show_when"] = {"field": "role_level", "regex_match": "^comm"}
    with pytest.raises(TemplateValidationError, match="must contain exactly one operator"):
        validate_template_definition(data)

    # 'in' operator must be non-empty list
    cond_field["show_when"] = {"field": "role_level", "in": "not a list"}
    with pytest.raises(TemplateValidationError, match="must be a non-empty list"):
        validate_template_definition(data)


@pytest.mark.parametrize(
    "cond_def",
    [
        {"field": "role_level", "equals": "committee"},
        {"field": "role_level", "not_equals": "board"},
        {"field": "role_level", "in": ["committee", "other"]},
        {"field": "role_level", "not_in": ["board"]},
    ],
)
def test_valid_conditions(cond_def: dict) -> None:
    data = sample_valid_template()
    data["steps"][0]["fields"][4]["show_when"] = cond_def
    validated = validate_template_definition(data)
    assert validated["steps"][0]["fields"][4]["show_when"] == cond_def


@pytest.mark.parametrize(
    "literal_default",
    [
        "A = B",
        "=SUM(1, 2)",
        "{{ user_input }}",
        "{{ example }}",
        "{% if role %}yes{% endif %}",
        "javascript:alert(1)",
        "eval(1 + 1)",
        "def foo(): pass",
        "lambda x: x",
    ],
)
def test_literal_code_like_defaults_are_accepted(literal_default: str) -> None:
    data = sample_valid_template()
    data["steps"][0]["fields"][0]["default"] = literal_default
    validated = validate_template_definition(data)
    assert validated["steps"][0]["fields"][0]["default"] == literal_default


def test_default_type_mismatch_rejected() -> None:
    data = sample_valid_template()

    # Checkbox with string default
    data["steps"][1]["fields"][2]["default"] = "yes"
    with pytest.raises(TemplateValidationError, match="default value for checkbox must be boolean"):
        validate_template_definition(data)

    data = sample_valid_template()
    # Number with string default
    data["steps"][0]["fields"][2]["default"] = "five"
    with pytest.raises(TemplateValidationError, match="default value for number must be int or float"):
        validate_template_definition(data)

    data = sample_valid_template()
    # Select with default not in options
    data["steps"][0]["fields"][3]["default"] = "non_existent_option"
    with pytest.raises(TemplateValidationError, match="is not in options"):
        validate_template_definition(data)


def test_validation_bounds_checking() -> None:
    data = sample_valid_template()

    # min_length > max_length
    data["steps"][0]["fields"][0]["min_length"] = 50
    data["steps"][0]["fields"][0]["max_length"] = 10
    with pytest.raises(TemplateValidationError, match="cannot be greater than 'max_length'"):
        validate_template_definition(data)

    data = sample_valid_template()
    # min > max for number
    data["steps"][0]["fields"][2]["min"] = 100
    data["steps"][0]["fields"][2]["max"] = 10
    with pytest.raises(TemplateValidationError, match="cannot be greater than 'max'"):
        validate_template_definition(data)

    data = sample_valid_template()
    # min_items > max_items for repeater
    data["steps"][1]["fields"][0]["min_items"] = 20
    data["steps"][1]["fields"][0]["max_items"] = 5
    with pytest.raises(TemplateValidationError, match="cannot be greater than 'max_items'"):
        validate_template_definition(data)

    data = sample_valid_template()
    # Invalid regex pattern
    data["steps"][0]["fields"][0]["pattern"] = "[a-z"
    with pytest.raises(TemplateValidationError, match="is not a valid regular expression"):
        validate_template_definition(data)


def test_field_attribute_type_constraints() -> None:
    data = sample_valid_template()
    # format on number field
    data["steps"][0]["fields"][2]["format"] = "email"
    with pytest.raises(TemplateValidationError, match="only valid for fields of type 'text'"):
        validate_template_definition(data)

    data = sample_valid_template()
    # min_length on number field
    data["steps"][0]["fields"][2]["min_length"] = 1
    with pytest.raises(TemplateValidationError, match="only valid for text/textarea fields"):
        validate_template_definition(data)

    data = sample_valid_template()
    # min on text field
    data["steps"][0]["fields"][0]["min"] = 1
    with pytest.raises(TemplateValidationError, match="only valid for number fields"):
        validate_template_definition(data)

    data = sample_valid_template()
    # min_items on text field
    data["steps"][0]["fields"][0]["min_items"] = 1
    with pytest.raises(TemplateValidationError, match="only valid for repeater/multiselect fields"):
        validate_template_definition(data)


def test_multiselect_and_repeater_defaults() -> None:
    data = sample_valid_template()
    # Add multiselect field
    data["steps"][0]["fields"].append({
        "id": "sports",
        "type": "multiselect",
        "label": "Idrætsgrene",
        "options": ["Fodbold", "Gymnastik", "Badminton"],
        "default": ["Fodbold", "Gymnastik"],
        "min_items": 1,
        "max_items": 3,
    })
    # Add valid repeater default
    data["steps"][1]["fields"][0]["default"] = [
        {"task_title": "Lede møder", "task_frequency": "Månedligt"}
    ]
    validated = validate_template_definition(data)
    assert validated["steps"][0]["fields"][-1]["default"] == ["Fodbold", "Gymnastik"]
    assert len(validated["steps"][1]["fields"][0]["default"]) == 1


def test_multiselect_invalid_defaults() -> None:
    data = sample_valid_template()
    data["steps"][0]["fields"].append({
        "id": "sports",
        "type": "multiselect",
        "label": "Idrætsgrene",
        "options": ["Fodbold", "Gymnastik"],
        "default": "not-a-list",
    })
    with pytest.raises(TemplateValidationError, match="must be a list"):
        validate_template_definition(data)

    data["steps"][0]["fields"][-1]["default"] = ["Fodbold", "UkendtSport"]
    with pytest.raises(TemplateValidationError, match="is not in options"):
        validate_template_definition(data)


def test_optional_field_metadata_help_placeholder_example() -> None:
    data = sample_valid_template()
    field = data["steps"][0]["fields"][0]
    field["help"] = "Angiv venligst rollens officielle titel"
    field["placeholder"] = "fx Kasserer"
    field["example"] = "Kasserer"
    field["pattern"] = "^[A-ZÆØÅ][a-zæøåA-ZÆØÅ0-9 ]+$"
    validated = validate_template_definition(data)
    f_val = validated["steps"][0]["fields"][0]
    assert f_val["help"] == "Angiv venligst rollens officielle titel"
    assert f_val["placeholder"] == "fx Kasserer"
    assert f_val["example"] == "Kasserer"
    assert f_val["pattern"] == "^[A-ZÆØÅ][a-zæøåA-ZÆØÅ0-9 ]+$"
