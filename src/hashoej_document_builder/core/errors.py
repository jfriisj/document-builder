"""Exceptions for template package loading, discovery, schema, and rendering pipeline."""

from __future__ import annotations


class TemplateError(Exception):
    """Base class for all template and rendering exceptions."""


class TemplateNotFoundError(TemplateError):
    """Raised when a template directory or required path does not exist."""


class TemplateMissingFileError(TemplateError):
    """Raised when a required file (e.g. template.yaml or document.docx) is missing."""


class TemplateYAMLError(TemplateError):
    """Raised when template.yaml is malformed or cannot be parsed as valid YAML."""


class TemplateValidationError(TemplateError):
    """Raised when a template fails schema or semantic domain validation."""


class DOCXBindingValidationError(TemplateValidationError):
    """Raised when document.docx violates the template binding or Jinja AST contract."""


class DocumentRenderingError(TemplateError):
    """Raised when DOCX template rendering fails."""


class PDFConversionError(TemplateError):
    """Raised when PDF conversion of a rendered DOCX fails."""


class PDFConversionUnavailableError(PDFConversionError):
    """Raised when the LibreOffice conversion executable is not installed or available."""
