"""Runtime validation and type coercion for user-entered values."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from datetime import datetime
import re
from typing import Any

from hashoej_document_builder.core.conditions import is_field_active

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TEL_REGEX = re.compile(r"^[0-9+\s().-]{5,}$")
URL_REGEX = re.compile(r"^https?://[^\s]+$")


@dataclass
class ValidationResult:
    """Result of validating runtime user-submitted values."""

    is_valid: bool
    coerced_values: dict[str, Any]
    errors: dict[str, str] = field(default_factory=dict)


def get_option_token(index: int) -> str:
    """Generate a deterministic opaque option token for HTML option values."""
    return f"opt_{index}"


def get_initial_repeater_row(repeater_def: dict[str, Any]) -> dict[str, Any]:
    """Generate an initialized row dictionary for a newly added repeater row."""
    row: dict[str, Any] = {}
    for child in repeater_def.get("fields", []):
        ctype = child.get("type")
        cid = child.get("id", "")
        if ctype == "info":
            continue

        if "default" in child:
            row[cid] = copy.deepcopy(child["default"])
        elif ctype == "checkbox":
            row[cid] = False
        elif ctype == "multiselect":
            row[cid] = []
        else:
            row[cid] = ""
    return row


def get_initial_values(form_definition: dict[str, Any]) -> dict[str, Any]:
    """Extract default initial values from a validated form definition using deep-copy isolation."""
    values: dict[str, Any] = {}
    for step in form_definition.get("steps", []):
        for f in step.get("fields", []):
            fid = f["id"]
            ftype = f.get("type")
            if ftype == "info":
                continue

            if "default" in f:
                values[fid] = copy.deepcopy(f["default"])
            else:
                if ftype == "checkbox":
                    values[fid] = False
                elif ftype in ("multiselect", "repeater"):
                    values[fid] = []
                else:
                    values[fid] = ""
    return values


def decode_option_token(field_def: dict[str, Any], token: Any) -> Any:
    """Decode an HTML option token (e.g. 'opt_0') to its exact YAML-declared value.

    Supported inputs:
      - 'opt_N': browser token referencing option at index N
      - exact typed scalar value matching an option value with strict type equality (type(opt_val) is type(token) and opt_val == token)
    """
    options = field_def.get("options", [])

    if isinstance(token, str) and token.startswith("opt_"):
        try:
            idx = int(token.split("_", 1)[1])
            if 0 <= idx < len(options):
                return copy.deepcopy(options[idx]["value"])
        except (ValueError, IndexError):
            pass
        return token

    # Check for already-typed internal representation with strict type matching
    for opt in options:
        opt_val = opt["value"]
        if type(opt_val) is type(token) and opt_val == token:
            return copy.deepcopy(opt_val)

    return token


def decode_field_option_tokens(field_def: dict[str, Any], val: Any) -> Any:
    """Decode single or multiselect option tokens for a field."""
    ftype = field_def.get("type")
    if ftype in ("select", "radio"):
        return decode_option_token(field_def, val)
    if ftype == "multiselect":
        if isinstance(val, list):
            return [decode_option_token(field_def, item) for item in val]
        elif val is not None:
            return [decode_option_token(field_def, val)]
        return []
    return val


def parse_form_data(raw_form: dict[str, Any]) -> dict[str, Any]:
    """Parse flat form dictionary with possible dot or bracket notation into nested structures.

    Supports:
      - 'field_id' -> scalar or list
      - 'repeater[0][child_id]' or 'repeater.0.child_id' -> list of dicts
      - row presence marker: 'repeater.0._row'
    """
    result: dict[str, Any] = {}
    repeater_buckets: dict[str, dict[int, dict[str, Any]]] = {}

    for key, val in raw_form.items():
        # Match dot notation: field.0.child
        dot_match = re.match(r"^([a-z0-9_]+)\.(\d+)\.([a-z0-9_]+)$", key)
        # Match bracket notation: field[0][child]
        bracket_match = re.match(r"^([a-z0-9_]+)\[(\d+)\]\[([a-z0-9_]+)\]$", key)

        match = dot_match or bracket_match
        if match:
            rep_id, row_idx_str, child_id = match.groups()
            row_idx = int(row_idx_str)
            if rep_id not in repeater_buckets:
                repeater_buckets[rep_id] = {}
            if row_idx not in repeater_buckets[rep_id]:
                repeater_buckets[rep_id][row_idx] = {}

            # Don't store private row marker as a child field value
            if child_id != "_row":
                repeater_buckets[rep_id][row_idx][child_id] = val
        else:
            result[key] = val

    # Assemble repeater rows sorted by row index
    for rep_id, rows_dict in repeater_buckets.items():
        sorted_indices = sorted(rows_dict.keys())
        result[rep_id] = [rows_dict[idx] for idx in sorted_indices]

    return result


def sanitize_step_input(step_def: dict[str, Any], parsed_form: dict[str, Any]) -> dict[str, Any]:
    """Sanitize submitted fields strictly against the step schema.

    - Preserves explicit empty browser controls (checkbox -> False, multiselect -> []).
    - Decodes option tokens (e.g. 'opt_0') to exact YAML-declared option values.
    - Drops unknown top-level keys, action, admin, info fields, and unapproved repeater child keys.
    """
    sanitized: dict[str, Any] = {}
    field_defs = {f["id"]: f for f in step_def.get("fields", [])}

    for fid, fdef in field_defs.items():
        ftype = fdef.get("type")
        if ftype == "info":
            continue

        if fid in parsed_form:
            val = parsed_form[fid]
            if ftype == "repeater":
                child_defs = {c["id"]: c for c in fdef.get("fields", []) if c.get("type") != "info"}
                if isinstance(val, list):
                    clean_rows = []
                    for row in val:
                        if isinstance(row, dict):
                            clean_row: dict[str, Any] = {}
                            for cid, cdef in child_defs.items():
                                ctype = cdef.get("type")
                                if cid in row:
                                    raw_cval = row[cid]
                                    decoded_cval = decode_field_option_tokens(cdef, raw_cval)
                                    clean_row[cid] = decoded_cval
                                else:
                                    # Explicit empty controls inside repeater row
                                    if ctype == "checkbox":
                                        clean_row[cid] = False
                                    elif ctype == "multiselect":
                                        clean_row[cid] = []
                            clean_rows.append(clean_row)
                    sanitized[fid] = clean_rows
                else:
                    sanitized[fid] = []
            elif ftype == "multiselect":
                decoded_multi = decode_field_option_tokens(fdef, val)
                sanitized[fid] = decoded_multi if isinstance(decoded_multi, list) else [decoded_multi]
            elif ftype in ("select", "radio"):
                sanitized[fid] = decode_field_option_tokens(fdef, val)
            elif ftype == "checkbox":
                sanitized[fid] = val in (True, "on", "true", "1", 1, "checked")
            else:
                sanitized[fid] = val
        else:
            # Field declared on step but omitted in POST payload
            if ftype == "checkbox":
                sanitized[fid] = False
            elif ftype == "multiselect":
                sanitized[fid] = []

    return sanitized


def normalize_step_values_for_conditions(
    step_def: dict[str, Any],
    raw_values: dict[str, Any],
) -> dict[str, Any]:
    """Normalize raw step inputs into typed Python representations for condition evaluation."""
    normalized: dict[str, Any] = {}

    for f in step_def.get("fields", []):
        fid = f["id"]
        ftype = f.get("type")
        if ftype == "info":
            continue

        raw = raw_values.get(fid)

        if ftype == "checkbox":
            normalized[fid] = raw in (True, "on", "true", "1", 1, "checked")
        elif ftype in ("select", "radio"):
            # If token, decode it
            decoded = decode_option_token(f, raw)
            normalized[fid] = decoded
        elif ftype == "multiselect":
            decoded = decode_field_option_tokens(f, raw)
            normalized[fid] = decoded if isinstance(decoded, list) else ([] if decoded is None else [decoded])
        elif ftype == "number":
            if raw is None or (isinstance(raw, str) and not raw.strip()):
                normalized[fid] = None
            elif isinstance(raw, (int, float)) and not isinstance(raw, bool):
                normalized[fid] = raw
            else:
                try:
                    s = str(raw).strip().replace(",", ".")
                    normalized[fid] = float(s) if "." in s else int(s)
                except (ValueError, TypeError):
                    normalized[fid] = raw
        else:
            normalized[fid] = str(raw).strip() if raw is not None and not isinstance(raw, (dict, list)) else raw

    return normalized


def validate_field_value(
    field_def: dict[str, Any],
    raw_val: Any,
) -> tuple[Any, str | None]:
    """Validate and coerce a single active field's value.

    Returns:
        (coerced_value, error_message or None)
    """
    ftype = field_def.get("type")
    fid = field_def.get("id", "")
    required = field_def.get("required", False)

    if ftype == "info":
        return None, None

    # Reject compound types on scalar fields
    if ftype in ("text", "textarea", "number", "date", "select", "radio", "checkbox"):
        if isinstance(raw_val, (dict, list)):
            return None, "Ugyldigt dataformat."

    if ftype == "checkbox":
        checked = raw_val in (True, "on", "true", "1", 1, "checked")
        if required and not checked:
            return False, "Dette felt skal markeres."
        return checked, None

    if ftype in ("text", "textarea"):
        if raw_val is None:
            coerced_str = ""
        else:
            coerced_str = str(raw_val).strip()

        if required and not coerced_str:
            return "", "Dette felt er påkrævet."

        if coerced_str:
            min_len = field_def.get("min_length")
            if min_len is not None and len(coerced_str) < min_len:
                return coerced_str, f"Skal være mindst {min_len} tegn."

            max_len = field_def.get("max_length")
            if max_len is not None and len(coerced_str) > max_len:
                return coerced_str, f"Må højst være {max_len} tegn."

            fmt = field_def.get("format")
            if fmt == "email" and not EMAIL_REGEX.match(coerced_str):
                return coerced_str, "Indtast en gyldig e-mailadresse."
            elif fmt == "tel" and not TEL_REGEX.match(coerced_str):
                return coerced_str, "Indtast et gyldigt telefonnummer."
            elif fmt == "url" and not URL_REGEX.match(coerced_str):
                return coerced_str, "Indtast en gyldig URL (f.eks. https://...)."

            pat = field_def.get("pattern")
            if pat:
                try:
                    if not re.search(pat, coerced_str):
                        return coerced_str, "Værdien matcher ikke det krævede format."
                except re.error:
                    pass

        return coerced_str, None

    if ftype == "number":
        if raw_val is None or (isinstance(raw_val, str) and not raw_val.strip()):
            if required:
                return None, "Dette felt er påkrævet."
            return None, None

        if isinstance(raw_val, bool):
            return None, "Indtast et gyldigt tal."

        try:
            if isinstance(raw_val, (int, float)):
                num_val = raw_val
            else:
                str_val = str(raw_val).strip().replace(",", ".")
                num_val = float(str_val) if "." in str_val else int(str_val)
        except (ValueError, TypeError):
            return raw_val, "Indtast et gyldigt tal."

        min_val = field_def.get("min")
        if min_val is not None and num_val < min_val:
            return num_val, f"Skal være mindst {min_val}."

        max_val = field_def.get("max")
        if max_val is not None and num_val > max_val:
            return num_val, f"Må højst være {max_val}."

        return num_val, None

    if ftype == "date":
        if raw_val is None or (isinstance(raw_val, str) and not raw_val.strip()):
            if required:
                return "", "Dette felt er påkrævet."
            return "", None

        date_str = str(raw_val).strip()
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return date_str, "Indtast en gyldig dato (ÅÅÅÅ-MM-DD)."

        return date_str, None

    if ftype in ("select", "radio"):
        options = field_def.get("options", [])
        decoded_val = decode_option_token(field_def, raw_val)

        if decoded_val is None or (isinstance(decoded_val, str) and not decoded_val.strip()):
            if required:
                return "", "Vælg venligst en mulighed."
            return "", None

        for opt in options:
            opt_val = opt["value"]
            # Strict type and value equality
            if type(opt_val) is type(decoded_val) and opt_val == decoded_val:
                return opt_val, None

        return raw_val, "Ugyldigt valg."

    if ftype == "multiselect":
        options = field_def.get("options", [])
        if raw_val is None:
            raw_list = []
        elif isinstance(raw_val, list):
            raw_list = raw_val
        elif isinstance(raw_val, (str, int, float, bool)):
            raw_list = [raw_val]
        else:
            return raw_val, "Ugyldigt valg."

        decoded_items = [decode_option_token(field_def, item) for item in raw_list]
        coerced_list = []

        for item in decoded_items:
            matched = False
            for opt in options:
                opt_val = opt["value"]
                if type(opt_val) is type(item) and opt_val == item:
                    coerced_list.append(opt_val)
                    matched = True
                    break
            if not matched:
                return raw_list, f"Ugyldigt valg: {item!r}."

        if required and len(coerced_list) == 0:
            return [], "Vælg mindst én mulighed."

        min_items = field_def.get("min_items")
        if min_items is not None and len(coerced_list) < min_items:
            return coerced_list, f"Vælg mindst {min_items} muligheder."

        max_items = field_def.get("max_items")
        if max_items is not None and len(coerced_list) > max_items:
            return coerced_list, f"Vælg højst {max_items} muligheder."

        return coerced_list, None

    if ftype == "repeater":
        child_defs = [c for c in field_def.get("fields", []) if c.get("type") != "info"]
        if raw_val is None:
            rows = []
        elif isinstance(raw_val, list):
            rows = raw_val
        else:
            return [], "Ugyldigt listeformat."

        # Enforce required repeater
        if required and len(rows) == 0:
            min_req = field_def.get("min_items", 1)
            return rows, f"Tilføj mindst {min_req} række{'r' if min_req > 1 else ''}."

        min_items = field_def.get("min_items")
        if min_items is not None and len(rows) < min_items:
            return rows, f"Tilføj mindst {min_items} række{'r' if min_items > 1 else ''}."

        max_items = field_def.get("max_items")
        if max_items is not None and len(rows) > max_items:
            return rows, f"Må højst indeholde {max_items} rækker."

        coerced_rows: list[dict[str, Any]] = []
        has_child_error = False

        for r_idx, row in enumerate(rows):
            row_dict = row if isinstance(row, dict) else {}
            coerced_row: dict[str, Any] = {}
            for child_def in child_defs:
                c_id = child_def["id"]
                c_val = row_dict.get(c_id)
                coerced_c_val, c_err = validate_field_value(child_def, c_val)
                coerced_row[c_id] = coerced_c_val
                if c_err:
                    has_child_error = True

            coerced_rows.append(coerced_row)

        if has_child_error:
            return coerced_rows, "Udfyld venligst alle påkrævede felter i listen."

        return coerced_rows, None

    return raw_val, None


def validate_step_values(
    step_def: dict[str, Any],
    submitted_values: dict[str, Any],
    current_values: dict[str, Any],
) -> ValidationResult:
    """Validate and coerce submitted values for a specific step.

    Builds a typed condition context to accurately evaluate show_when rules.
    """
    # Sanitize input against step schema and decode option tokens
    sanitized_input = sanitize_step_input(step_def, submitted_values)

    # Normalize submitted values for typed condition evaluation
    normalized_submitted = normalize_step_values_for_conditions(step_def, sanitized_input)

    # Context: authoritative current values overlaid with normalized submitted values
    merged_context = dict(current_values)
    merged_context.update(normalized_submitted)

    coerced_step_values: dict[str, Any] = {}
    errors: dict[str, str] = {}
    is_valid = True

    for field_def in step_def.get("fields", []):
        fid = field_def["id"]
        ftype = field_def.get("type")

        # Evaluate visibility using typed condition context
        if not is_field_active(field_def, merged_context):
            continue

        if ftype == "info":
            continue

        raw_val = sanitized_input.get(fid)

        if ftype == "repeater":
            child_defs = [c for c in field_def.get("fields", []) if c.get("type") != "info"]
            rows = raw_val if isinstance(raw_val, list) else []
            min_items = field_def.get("min_items")
            max_items = field_def.get("max_items")
            required = field_def.get("required", False)

            if required and len(rows) == 0:
                min_req = min_items or 1
                errors[fid] = f"Tilføj mindst {min_req} række{'r' if min_req > 1 else ''}."
                is_valid = False
            elif min_items is not None and len(rows) < min_items:
                errors[fid] = f"Tilføj mindst {min_items} række{'r' if min_items > 1 else ''}."
                is_valid = False

            if max_items is not None and len(rows) > max_items:
                errors[fid] = f"Må højst indeholde {max_items} rækker."
                is_valid = False

            coerced_rows: list[dict[str, Any]] = []
            for r_idx, row in enumerate(rows):
                row_dict = row if isinstance(row, dict) else {}
                coerced_row: dict[str, Any] = {}
                for child_def in child_defs:
                    cid = child_def["id"]
                    c_raw = row_dict.get(cid)
                    c_coerced, c_err = validate_field_value(child_def, c_raw)
                    coerced_row[cid] = c_coerced
                    if c_err:
                        errors[f"{fid}.{r_idx}.{cid}"] = c_err
                        if fid not in errors:
                            errors[fid] = "Udfyld venligst alle påkrævede felter i listen."
                        is_valid = False
                coerced_rows.append(coerced_row)
            coerced_step_values[fid] = coerced_rows
        else:
            coerced_val, err_msg = validate_field_value(field_def, raw_val)
            coerced_step_values[fid] = coerced_val
            if err_msg:
                errors[fid] = err_msg
                is_valid = False

    return ValidationResult(
        is_valid=is_valid,
        coerced_values=coerced_step_values,
        errors=errors,
    )


def validate_all_steps_values(
    form_definition: dict[str, Any],
    values: dict[str, Any],
) -> ValidationResult:
    """Validate all steps across the entire template against authoritative session values."""
    all_coerced: dict[str, Any] = {}
    all_errors: dict[str, str] = {}
    overall_valid = True

    for step in form_definition.get("steps", []):
        step_res = validate_step_values(step, values, values)
        all_coerced.update(step_res.coerced_values)
        all_errors.update(step_res.errors)
        if not step_res.is_valid:
            overall_valid = False

    return ValidationResult(
        is_valid=overall_valid,
        coerced_values=all_coerced,
        errors=all_errors,
    )


def get_field_display_label(field_def: dict[str, Any], value: Any) -> Any:
    """Resolve raw option values to human-readable option labels for review and preview."""
    ftype = field_def.get("type")
    options = field_def.get("options", [])
    if not options or value is None:
        return value

    if ftype in ("select", "radio"):
        for opt in options:
            if type(opt["value"]) is type(value) and opt["value"] == value:
                return opt["label"]
        return value

    if ftype == "multiselect":
        if isinstance(value, list):
            labels = []
            for item in value:
                matched = False
                for opt in options:
                    if type(opt["value"]) is type(item) and opt["value"] == item:
                        labels.append(opt["label"])
                        matched = True
                        break
                if not matched:
                    labels.append(str(item))
            return labels
        return value

    return value
