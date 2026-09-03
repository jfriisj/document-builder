"""Discovery and loading of template packages from the filesystem."""

from __future__ import annotations

from pathlib import Path
import yaml

from hashoej_document_builder.core.docx_binding import validate_docx_binding
from hashoej_document_builder.core.errors import (
    TemplateMissingFileError,
    TemplateNotFoundError,
    TemplateValidationError,
    TemplateYAMLError,
)
from hashoej_document_builder.core.models import TemplatePackage
from hashoej_document_builder.core.schema import validate_template_definition


def load_template_package(package_dir: Path | str) -> TemplatePackage:
    """Load and validate a single template package from a directory path.

    Raises:
        TemplateNotFoundError: If package_dir does not exist or is not a directory.
        TemplateMissingFileError: If template.yaml or document.docx is missing or not a regular file.
        TemplateYAMLError: If template.yaml cannot be read or parsed as YAML.
        TemplateValidationError: If the template fails schema or semantic validation.
    """
    path = Path(package_dir)
    if not path.exists() or not path.is_dir():
        raise TemplateNotFoundError(f"Template package directory not found: {path}")

    yaml_path = path / "template.yaml"
    docx_path = path / "document.docx"

    if not yaml_path.is_file():
        raise TemplateMissingFileError(f"Missing required regular file 'template.yaml' in {path}")
    if not docx_path.is_file():
        raise TemplateMissingFileError(f"Missing required regular file 'document.docx' in {path}")

    try:
        content = yaml_path.read_text(encoding="utf-8")
        raw_data = yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise TemplateYAMLError(f"Invalid YAML in {yaml_path}: {exc}") from exc
    except (OSError, UnicodeDecodeError) as exc:
        raise TemplateYAMLError(f"Could not read {yaml_path}: {exc}") from exc

    if raw_data is None or not isinstance(raw_data, dict):
        raise TemplateYAMLError(f"Template definition in {yaml_path} must be a non-empty YAML object/mapping.")

    validated = validate_template_definition(raw_data)
    validate_docx_binding(docx_path, validated)

    return TemplatePackage(
        id=validated["id"],
        version=validated["version"],
        enabled=validated["enabled"],
        title=validated["title"],
        category=validated["category"],
        description=validated["description"],
        path=path.resolve(),
        form_definition=validated,
        document_template=docx_path.resolve(),
    )


def discover_templates(template_root: Path | str) -> list[TemplatePackage]:
    """Discover all valid template packages within a root directory.

    Returns a list of TemplatePackage domain objects sorted deterministically by ID.

    Raises:
        TemplateNotFoundError: If template_root does not exist or is not a directory.
        TemplateValidationError: If duplicate template IDs are detected across packages.
    """
    root = Path(template_root)
    if not root.exists() or not root.is_dir():
        raise TemplateNotFoundError(f"Template root directory not found: {root}")

    packages: list[TemplatePackage] = []
    seen_ids: dict[str, Path] = {}

    # Inspect all immediate subdirectories
    subdirs = sorted([d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")])

    for subdir in subdirs:
        package = load_template_package(subdir)
        if package.id in seen_ids:
            first_path = seen_ids[package.id]
            raise TemplateValidationError(
                f"Duplicate template id {package.id!r} found in {subdir.name!r} and {first_path.name!r}. "
                "Only one installed version of each template ID may exist in the template root."
            )
        seen_ids[package.id] = subdir
        packages.append(package)

    # Deterministic sorting by template id
    packages.sort(key=lambda p: p.id)
    return packages


def discover_enabled_templates(template_root: Path | str) -> list[TemplatePackage]:
    """Discover all valid and enabled template packages within a root directory."""
    return [p for p in discover_templates(template_root) if p.enabled]
