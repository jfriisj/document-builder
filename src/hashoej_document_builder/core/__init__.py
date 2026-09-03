from hashoej_document_builder.core.artifacts import ArtifactManager
from hashoej_document_builder.core.conditions import evaluate_condition, is_field_active
from hashoej_document_builder.core.discovery import (
    discover_enabled_templates,
    discover_templates,
    load_template_package,
)
from hashoej_document_builder.core.docx_binding import extract_docx_xml, validate_docx_binding
from hashoej_document_builder.core.errors import (
    DOCXBindingValidationError,
    DocumentRenderingError,
    PDFConversionError,
    PDFConversionUnavailableError,
    TemplateError,
    TemplateMissingFileError,
    TemplateNotFoundError,
    TemplateValidationError,
    TemplateYAMLError,
)
from hashoej_document_builder.core.models import (
    GeneratedArtifact,
    GenerationSession,
    TemplatePackage,
    utc_now,
)
from hashoej_document_builder.core.pdf import convert_docx_to_pdf
from hashoej_document_builder.core.rendering import build_render_context, render_docx
from hashoej_document_builder.core.session import SessionStore
from hashoej_document_builder.core.validation import (
    ValidationResult,
    decode_field_option_tokens,
    decode_option_token,
    get_field_display_label,
    get_initial_repeater_row,
    get_initial_values,
    get_option_token,
    normalize_step_values_for_conditions,
    parse_form_data,
    sanitize_step_input,
    validate_all_steps_values,
    validate_field_value,
    validate_step_values,
)

__all__ = [
    "ArtifactManager",
    "DOCXBindingValidationError",
    "DocumentRenderingError",
    "GeneratedArtifact",
    "GenerationSession",
    "PDFConversionError",
    "PDFConversionUnavailableError",
    "SessionStore",
    "TemplateError",
    "TemplateMissingFileError",
    "TemplateNotFoundError",
    "TemplatePackage",
    "TemplateValidationError",
    "TemplateYAMLError",
    "ValidationResult",
    "build_render_context",
    "convert_docx_to_pdf",
    "decode_field_option_tokens",
    "decode_option_token",
    "discover_enabled_templates",
    "discover_templates",
    "evaluate_condition",
    "extract_docx_xml",
    "get_field_display_label",
    "get_initial_repeater_row",
    "get_initial_values",
    "get_option_token",
    "is_field_active",
    "load_template_package",
    "normalize_step_values_for_conditions",
    "parse_form_data",
    "render_docx",
    "sanitize_step_input",
    "utc_now",
    "validate_all_steps_values",
    "validate_docx_binding",
    "validate_field_value",
    "validate_step_values",
]
