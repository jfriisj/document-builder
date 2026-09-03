"""Schema validation for template.yaml definitions."""

from __future__ import annotations

import re
from typing import Any

from hashoej_document_builder.core.errors import TemplateValidationError

TEMPLATE_ID_PATTERN = re.compile(r"^[a-z0-9]+([-_][a-z0-9]+)*$")
STEP_ID_PATTERN = re.compile(r"^[a-z0-9]+([-_][a-z0-9]+)*$")
FIELD_ID_PATTERN = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")

SUPPORTED_FIELD_TYPES = {
    "text",
    "textarea",
    "number",
    "date",
    "select",
    "radio",
    "checkbox",
    "multiselect",
    "repeater",
    "info",
}

SUPPORTED_TEXT_FORMATS = {
    "email",
    "tel",
    "url",
}

SUPPORTED_CONDITION_OPERATORS = {
    "equals",
    "not_equals",
    "in",
    "not_in",
}

SUPPORTED_PURPOSES = {
    "acknowledgement",
    "consent",
}

SUPPORTED_INFO_VARIANTS = {
    "privacy",
    "notice",
    "warning",
    "tip",
    "default",
}


def validate_template_definition(raw_data: Any) -> dict[str, Any]:
    """Validate a raw template dictionary against the specification schema.

    Returns the validated template dictionary or raises TemplateValidationError.
    """
    if not isinstance(raw_data, dict):
        raise TemplateValidationError("Template definition must be a YAML dictionary/object.")

    # 1. Top-level metadata
    template_id = raw_data.get("id")
    if not isinstance(template_id, str) or not TEMPLATE_ID_PATTERN.match(template_id):
        raise TemplateValidationError(
            f"Invalid or missing template 'id': {template_id!r}. Must match regex {TEMPLATE_ID_PATTERN.pattern}"
        )

    version = raw_data.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise TemplateValidationError(f"Invalid or missing template 'version': {version!r}. Must be integer >= 1.")

    enabled = raw_data.get("enabled")
    if not isinstance(enabled, bool):
        raise TemplateValidationError(f"Invalid or missing template 'enabled': {enabled!r}. Must be boolean.")

    for str_field in ("title", "category", "description"):
        val = raw_data.get(str_field)
        if not isinstance(val, str) or not val.strip():
            raise TemplateValidationError(
                f"Invalid or missing template '{str_field}': {val!r}. Must be a non-empty string."
            )

    steps_data = raw_data.get("steps")
    if not isinstance(steps_data, list) or len(steps_data) == 0:
        raise TemplateValidationError("Template 'steps' must be a non-empty list of steps.")

    # 2. Validate steps and collect all top-level field IDs and field definitions for whole-template validation
    step_ids: set[str] = set()
    top_level_fields_by_id: dict[str, dict[str, Any]] = {}
    validated_steps: list[dict[str, Any]] = []

    for step_idx, step_raw in enumerate(steps_data):
        if not isinstance(step_raw, dict):
            raise TemplateValidationError(f"Step at index {step_idx} must be a dictionary.")

        step_id = step_raw.get("id")
        if not isinstance(step_id, str) or not STEP_ID_PATTERN.match(step_id):
            raise TemplateValidationError(
                f"Invalid or missing step 'id' at index {step_idx}: {step_id!r}. Must match {STEP_ID_PATTERN.pattern}"
            )

        if step_id in step_ids:
            raise TemplateValidationError(f"Duplicate step id: {step_id!r}")
        step_ids.add(step_id)

        step_title = step_raw.get("title")
        if not isinstance(step_title, str) or not step_title.strip():
            raise TemplateValidationError(f"Invalid or missing step 'title' in step {step_id!r}")

        fields_data = step_raw.get("fields")
        if not isinstance(fields_data, list) or len(fields_data) == 0:
            raise TemplateValidationError(f"Step {step_id!r} must contain a non-empty list of 'fields'.")

        validated_fields: list[dict[str, Any]] = []
        for field_idx, field_raw in enumerate(fields_data):
            if not isinstance(field_raw, dict):
                raise TemplateValidationError(
                    f"Field at index {field_idx} in step {step_id!r} must be a dictionary."
                )

            field_id = field_raw.get("id")
            if not isinstance(field_id, str) or not FIELD_ID_PATTERN.match(field_id):
                raise TemplateValidationError(
                    f"Invalid or missing field 'id' at index {field_idx} in step {step_id!r}: {field_id!r}. "
                    f"Field IDs must be lowercase snake_case matching {FIELD_ID_PATTERN.pattern}."
                )

            if field_id in top_level_fields_by_id:
                raise TemplateValidationError(
                    f"Duplicate top-level field id {field_id!r} found in step {step_id!r}."
                )

            validated_field = _validate_field(field_raw, step_id=step_id, is_child=False)
            top_level_fields_by_id[field_id] = validated_field
            validated_fields.append(validated_field)

        validated_step: dict[str, Any] = {
            "id": step_id,
            "title": step_title.strip(),
            "fields": validated_fields,
        }
        if "description" in step_raw and isinstance(step_raw["description"], str):
            validated_step["description"] = step_raw["description"].strip()

        validated_steps.append(validated_step)

    # 3. Whole-template validation: validate show_when cross-field references
    _validate_all_conditions(top_level_fields_by_id)

    validated_doc: dict[str, Any] = {
        "id": template_id,
        "version": version,
        "enabled": enabled,
        "title": raw_data["title"].strip(),
        "category": raw_data["category"].strip(),
        "description": raw_data["description"].strip(),
        "steps": validated_steps,
    }

    return validated_doc


def _validate_field(field_raw: dict[str, Any], step_id: str, is_child: bool = False) -> dict[str, Any]:
    """Validate an individual field definition."""
    field_id = field_raw.get("id")
    if not isinstance(field_id, str) or not FIELD_ID_PATTERN.match(field_id):
        raise TemplateValidationError(
            f"Invalid field id {field_id!r}. Must be lowercase snake_case matching {FIELD_ID_PATTERN.pattern}"
        )

    field_type = field_raw.get("type")
    if field_type not in SUPPORTED_FIELD_TYPES:
        raise TemplateValidationError(
            f"Unsupported field type {field_type!r} for field {field_id!r} in step {step_id!r}. "
            f"Allowed types: {sorted(SUPPORTED_FIELD_TYPES)}"
        )

    # Implementation constraint: nested repeaters are rejected for Milestone 2.
    # This is an implementation constraint rather than an authoritative product/schema decision.
    if is_child and field_type == "repeater":
        raise TemplateValidationError(
            f"Nested repeater field {field_id!r} is not allowed inside a parent repeater."
        )

    # Implementation constraint: conditional logic inside repeater child items is not supported in Milestone 2.
    # This may only be generalized if one of the real 21 templates requires it.
    if is_child and "show_when" in field_raw:
        raise TemplateValidationError(
            f"Repeater child field {field_id!r} contains 'show_when'. "
            "Conditional logic on repeater child fields is not supported in Milestone 2."
        )

    validated: dict[str, Any] = {
        "id": field_id,
        "type": field_type,
    }

    # label vs text for info
    if field_type == "info":
        info_text = field_raw.get("text")
        if not isinstance(info_text, str) or not info_text.strip():
            raise TemplateValidationError(
                f"Field {field_id!r} of type 'info' must have non-empty 'text'."
            )
        validated["text"] = info_text.strip()

        if "label" in field_raw:
            if isinstance(field_raw["label"], str):
                validated["label"] = field_raw["label"].strip()

        if "variant" in field_raw:
            variant = field_raw["variant"]
            if variant not in SUPPORTED_INFO_VARIANTS:
                raise TemplateValidationError(
                    f"Unsupported variant {variant!r} for info field {field_id!r}. "
                    f"Allowed variants: {sorted(SUPPORTED_INFO_VARIANTS)}"
                )
            validated["variant"] = variant
    else:
        label = field_raw.get("label")
        if not isinstance(label, str) or not label.strip():
            raise TemplateValidationError(
                f"Field {field_id!r} in step {step_id!r} must have a non-empty 'label'."
            )
        validated["label"] = label.strip()

    # Optional metadata: help, placeholder, example
    for opt_key in ("help", "placeholder", "example"):
        if opt_key in field_raw:
            opt_val = field_raw[opt_key]
            if opt_val is not None and not isinstance(opt_val, str):
                raise TemplateValidationError(
                    f"Field {field_id!r} '{opt_key}' must be a string if provided."
                )
            if isinstance(opt_val, str):
                validated[opt_key] = opt_val

    # required
    if "required" in field_raw:
        req = field_raw["required"]
        if not isinstance(req, bool):
            raise TemplateValidationError(
                f"Field {field_id!r} 'required' attribute must be boolean."
            )
        validated["required"] = req
    else:
        validated["required"] = False

    # format (only valid for text, must be one of SUPPORTED_TEXT_FORMATS)
    if "format" in field_raw:
        fmt = field_raw["format"]
        if field_type != "text":
            raise TemplateValidationError(
                f"Field {field_id!r}: 'format' is only valid for fields of type 'text'."
            )
        if not isinstance(fmt, str) or not fmt.strip():
            raise TemplateValidationError(
                f"Field {field_id!r}: 'format' must be a non-empty string."
            )
        fmt_clean = fmt.strip()
        if fmt_clean not in SUPPORTED_TEXT_FORMATS:
            raise TemplateValidationError(
                f"Field {field_id!r}: unsupported text format {fmt_clean!r}. "
                f"Allowed formats: {sorted(SUPPORTED_TEXT_FORMATS)}"
            )
        validated["format"] = fmt_clean

    # pattern
    if "pattern" in field_raw:
        pattern = field_raw["pattern"]
        if not isinstance(pattern, str):
            raise TemplateValidationError(
                f"Field {field_id!r}: 'pattern' must be a regex string."
            )
        try:
            re.compile(pattern)
        except re.error as err:
            raise TemplateValidationError(
                f"Field {field_id!r}: 'pattern' is not a valid regular expression: {err}"
            ) from err
        validated["pattern"] = pattern

    # min_length / max_length (text, textarea)
    if "min_length" in field_raw:
        min_len = field_raw["min_length"]
        if field_type not in ("text", "textarea"):
            raise TemplateValidationError(
                f"Field {field_id!r}: 'min_length' is only valid for text/textarea fields."
            )
        if not isinstance(min_len, int) or isinstance(min_len, bool) or min_len < 0:
            raise TemplateValidationError(
                f"Field {field_id!r}: 'min_length' must be a non-negative integer."
            )
        validated["min_length"] = min_len

    if "max_length" in field_raw:
        max_len = field_raw["max_length"]
        if field_type not in ("text", "textarea"):
            raise TemplateValidationError(
                f"Field {field_id!r}: 'max_length' is only valid for text/textarea fields."
            )
        if not isinstance(max_len, int) or isinstance(max_len, bool) or max_len < 0:
            raise TemplateValidationError(
                f"Field {field_id!r}: 'max_length' must be a non-negative integer."
            )
        validated["max_length"] = max_len

    if "min_length" in validated and "max_length" in validated:
        if validated["min_length"] > validated["max_length"]:
            raise TemplateValidationError(
                f"Field {field_id!r}: 'min_length' ({validated['min_length']}) cannot be greater than 'max_length' ({validated['max_length']})."
            )

    # min / max (number)
    if "min" in field_raw:
        min_val = field_raw["min"]
        if field_type != "number":
            raise TemplateValidationError(f"Field {field_id!r}: 'min' is only valid for number fields.")
        if isinstance(min_val, bool) or not isinstance(min_val, (int, float)):
            raise TemplateValidationError(f"Field {field_id!r}: 'min' must be a number.")
        validated["min"] = min_val

    if "max" in field_raw:
        max_val = field_raw["max"]
        if field_type != "number":
            raise TemplateValidationError(f"Field {field_id!r}: 'max' is only valid for number fields.")
        if isinstance(max_val, bool) or not isinstance(max_val, (int, float)):
            raise TemplateValidationError(f"Field {field_id!r}: 'max' must be a number.")
        validated["max"] = max_val

    if "min" in validated and "max" in validated:
        if validated["min"] > validated["max"]:
            raise TemplateValidationError(
                f"Field {field_id!r}: 'min' ({validated['min']}) cannot be greater than 'max' ({validated['max']})."
            )

    # min_items / max_items (repeater, multiselect)
    if "min_items" in field_raw:
        min_items = field_raw["min_items"]
        if field_type not in ("repeater", "multiselect"):
            raise TemplateValidationError(
                f"Field {field_id!r}: 'min_items' is only valid for repeater/multiselect fields."
            )
        if not isinstance(min_items, int) or isinstance(min_items, bool) or min_items < 0:
            raise TemplateValidationError(
                f"Field {field_id!r}: 'min_items' must be a non-negative integer."
            )
        validated["min_items"] = min_items

    if "max_items" in field_raw:
        max_items = field_raw["max_items"]
        if field_type not in ("repeater", "multiselect"):
            raise TemplateValidationError(
                f"Field {field_id!r}: 'max_items' is only valid for repeater/multiselect fields."
            )
        if not isinstance(max_items, int) or isinstance(max_items, bool) or max_items < 0:
            raise TemplateValidationError(
                f"Field {field_id!r}: 'max_items' must be a non-negative integer."
            )
        validated["max_items"] = max_items

    if "min_items" in validated and "max_items" in validated:
        if validated["min_items"] > validated["max_items"]:
            raise TemplateValidationError(
                f"Field {field_id!r}: 'min_items' ({validated['min_items']}) cannot be greater than 'max_items' ({validated['max_items']})."
            )

    # Options for select, radio, multiselect
    if field_type in ("select", "radio", "multiselect"):
        options_raw = field_raw.get("options")
        if not isinstance(options_raw, list) or len(options_raw) == 0:
            raise TemplateValidationError(
                f"Field {field_id!r} of type {field_type!r} must have a non-empty 'options' list."
            )
        normalized_options: list[dict[str, Any]] = []
        option_values: set[Any] = set()

        for opt_idx, opt in enumerate(options_raw):
            if isinstance(opt, (str, int, float, bool)):
                if isinstance(opt, str):
                    if not opt.strip():
                        raise TemplateValidationError(
                            f"Field {field_id!r} option at index {opt_idx} cannot be empty."
                        )
                    val = opt.strip()
                    lbl = opt.strip()
                else:
                    val = opt
                    lbl = str(opt)
            elif isinstance(opt, dict):
                val = opt.get("value")
                lbl = opt.get("label")
                if val is None or (isinstance(val, str) and not val.strip()):
                    raise TemplateValidationError(
                        f"Field {field_id!r} option at index {opt_idx} missing 'value'."
                    )
                if not isinstance(val, (str, int, float, bool)) or isinstance(val, (list, dict)):
                    raise TemplateValidationError(
                        f"Field {field_id!r} option at index {opt_idx} has invalid value {val!r}. "
                        "Option values must be scalar strings, numbers, or booleans."
                    )
                if not isinstance(lbl, str) or not lbl.strip():
                    raise TemplateValidationError(
                        f"Field {field_id!r} option at index {opt_idx} missing 'label'."
                    )
                if isinstance(val, str):
                    val = val.strip()
                lbl = lbl.strip()
            else:
                raise TemplateValidationError(
                    f"Field {field_id!r} option at index {opt_idx} must be a scalar string/number or an object with 'value' and 'label'."
                )

            opt_key = (type(val), val)
            try:
                if opt_key in option_values:
                    raise TemplateValidationError(
                        f"Field {field_id!r} contains duplicate option value: {val!r}"
                    )
                option_values.add(opt_key)
            except TypeError as err:
                raise TemplateValidationError(
                    f"Field {field_id!r} option value {val!r} is not a valid scalar/hashable value."
                ) from err

            normalized_options.append({"value": val, "label": lbl})

        validated["options"] = normalized_options

    # Purpose (acknowledgement / consent restricted to checkbox fields)
    if "purpose" in field_raw:
        purpose = field_raw["purpose"]
        if field_type != "checkbox":
            raise TemplateValidationError(
                f"Field {field_id!r}: 'purpose' is only allowed on 'checkbox' fields, not {field_type!r}."
            )
        if purpose not in SUPPORTED_PURPOSES:
            raise TemplateValidationError(
                f"Unsupported purpose {purpose!r} on field {field_id!r}. "
                f"Allowed values: {sorted(SUPPORTED_PURPOSES)}"
            )
        validated["purpose"] = purpose

    # Repeater child fields
    if field_type == "repeater":
        child_fields_raw = field_raw.get("fields")
        if not isinstance(child_fields_raw, list) or len(child_fields_raw) == 0:
            raise TemplateValidationError(
                f"Repeater field {field_id!r} in step {step_id!r} must contain a non-empty 'fields' list."
            )

        child_ids: set[str] = set()
        validated_children: list[dict[str, Any]] = []

        for child_raw in child_fields_raw:
            if not isinstance(child_raw, dict):
                raise TemplateValidationError(
                    f"Child field in repeater {field_id!r} must be a dictionary."
                )
            cid = child_raw.get("id")
            if not isinstance(cid, str) or not FIELD_ID_PATTERN.match(cid):
                raise TemplateValidationError(
                    f"Invalid child field id {cid!r} in repeater {field_id!r}. Must be lowercase snake_case."
                )
            if cid in child_ids:
                raise TemplateValidationError(
                    f"Duplicate child field id {cid!r} inside repeater {field_id!r}."
                )
            child_ids.add(cid)
            validated_child = _validate_field(child_raw, step_id=step_id, is_child=True)
            validated_children.append(validated_child)

        validated["fields"] = validated_children

    # show_when (raw validation of condition syntax)
    if "show_when" in field_raw:
        show_when = field_raw["show_when"]
        if not isinstance(show_when, dict):
            raise TemplateValidationError(
                f"Field {field_id!r}: 'show_when' must be a dictionary."
            )
        target_field = show_when.get("field")
        if not isinstance(target_field, str) or not target_field.strip():
            raise TemplateValidationError(
                f"Field {field_id!r}: 'show_when' must specify a 'field' string."
            )
        if target_field == field_id:
            raise TemplateValidationError(
                f"Field {field_id!r}: 'show_when' cannot reference itself."
            )

        operators_present = [op for op in show_when if op in SUPPORTED_CONDITION_OPERATORS]
        if len(operators_present) == 0:
            raise TemplateValidationError(
                f"Field {field_id!r}: 'show_when' must contain exactly one operator from {sorted(SUPPORTED_CONDITION_OPERATORS)}."
            )
        if len(operators_present) > 1:
            raise TemplateValidationError(
                f"Field {field_id!r}: 'show_when' contains multiple operators: {operators_present}. Only one allowed."
            )

        op = operators_present[0]
        # Check for unknown extra keys in show_when
        extra_keys = set(show_when.keys()) - {"field", op}
        if extra_keys:
            raise TemplateValidationError(
                f"Field {field_id!r}: 'show_when' contains invalid keys: {sorted(extra_keys)}."
            )

        op_val = show_when[op]
        if op in ("in", "not_in"):
            if not isinstance(op_val, list) or len(op_val) == 0:
                raise TemplateValidationError(
                    f"Field {field_id!r}: 'show_when' operator '{op}' must be a non-empty list."
                )
        else:
            if isinstance(op_val, (list, dict)):
                raise TemplateValidationError(
                    f"Field {field_id!r}: 'show_when' operator '{op}' requires a scalar value, got {type(op_val).__name__}."
                )

        validated["show_when"] = {
            "field": target_field.strip(),
            op: op_val,
        }

    # default validation
    if "default" in field_raw:
        default_val = field_raw["default"]
        _validate_default_value(field_id, field_type, default_val, validated.get("options"))
        validated["default"] = default_val

    return validated


def _validate_default_value(
    field_id: str,
    field_type: str,
    default_val: Any,
    options: list[dict[str, Any]] | None,
) -> None:
    """Validate that a default value is type-compatible with the field definition."""
    if field_type == "info":
        raise TemplateValidationError(
            f"Field {field_id!r}: field of type 'info' cannot have a 'default' value."
        )
    elif field_type == "checkbox":
        if not isinstance(default_val, bool):
            raise TemplateValidationError(
                f"Field {field_id!r}: default value for checkbox must be boolean, got {default_val!r}."
            )
    elif field_type == "number":
        if isinstance(default_val, bool) or not isinstance(default_val, (int, float)):
            raise TemplateValidationError(
                f"Field {field_id!r}: default value for number must be int or float, got {default_val!r}."
            )
    elif field_type in ("text", "textarea", "date"):
        if not isinstance(default_val, str):
            raise TemplateValidationError(
                f"Field {field_id!r}: default value for {field_type} must be string, got {default_val!r}."
            )
    elif field_type in ("select", "radio"):
        valid_options = options or []
        is_valid = any(type(opt["value"]) is type(default_val) and opt["value"] == default_val for opt in valid_options)
        if not is_valid:
            valid_strs = [str(opt["value"]) for opt in valid_options]
            raise TemplateValidationError(
                f"Field {field_id!r}: default value {default_val!r} is not in options: {sorted(valid_strs)}."
            )
    elif field_type == "multiselect":
        if not isinstance(default_val, list):
            raise TemplateValidationError(
                f"Field {field_id!r}: default value for multiselect must be a list."
            )
        valid_options = options or []
        for item in default_val:
            is_valid = any(type(opt["value"]) is type(item) and opt["value"] == item for opt in valid_options)
            if not is_valid:
                valid_strs = [str(opt["value"]) for opt in valid_options]
                raise TemplateValidationError(
                    f"Field {field_id!r}: multiselect default item {item!r} is not in options: {sorted(valid_strs)}."
                )
    elif field_type == "repeater":
        if not isinstance(default_val, list):
            raise TemplateValidationError(
                f"Field {field_id!r}: default value for repeater must be a list of objects."
            )
        for item in default_val:
            if not isinstance(item, dict):
                raise TemplateValidationError(
                    f"Field {field_id!r}: repeater default items must be dictionaries/objects."
                )


def _validate_all_conditions(fields_by_id: dict[str, dict[str, Any]]) -> None:
    """Validate that all show_when conditions reference existing, valid controlling fields."""
    for field_id, field in fields_by_id.items():
        if "show_when" in field:
            target_id = field["show_when"]["field"]
            if target_id not in fields_by_id:
                raise TemplateValidationError(
                    f"Field {field_id!r} has condition referencing unknown field {target_id!r}."
                )
            target_field = fields_by_id[target_id]
            if target_field.get("type") == "info":
                raise TemplateValidationError(
                    f"Field {field_id!r} has condition referencing info field {target_id!r} which has no input value."
                )
