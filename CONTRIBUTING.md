# Contributing to Document Builder

Thank you for your interest in contributing to Document Builder!

---

## 1. Development Setup

The project uses [`uv`](https://docs.astral.sh/uv/) for Python package management:

```bash
# Clone the repository
git clone <repo-url>
cd document-builder

# Install dependencies and sync virtual environment
uv sync

# Start the local development server with hot-reload
uv run uvicorn hashoej_document_builder.web.app:app --reload
```

---

## 2. Architecture Boundaries

Contributors must strictly adhere to the project's architectural principles:
- **Core Independence**: The core domain logic (`src/hashoej_document_builder/core/`) must remain independent of web frameworks (FastAPI), HTML/HTMX, and HTTP concerns.
- **Declarative Template Rule**: Template-specific behavior belongs exclusively in declarative configuration:
  - `template.yaml` (form structure, validation, step definitions, conditional rules)
  - `document.docx` (layout, formatting, docxtpl placeholders)
  - `assets/` (optional template-specific static assets)
- **No Document-Specific Production Python**: The application runtime is a generic engine. Do not write template-specific Python classes, hardcoded field mappings, or branches on template IDs in the core or web layers.
- **Privacy Activation Gates**: High-sensitivity templates (specifically `templates/hif-17-incident/`) have `enabled: false` due to potential health and injury data. This privacy gate must not be enabled casually without explicit legal and privacy sign-off.

---

## 3. Testing and Compatibility

Before submitting contributions, ensure all test gates pass:

```bash
# Run host test suite (skips LibreOffice PDF conversion if soffice is not installed locally)
uv run pytest -v

# Run full regression suite inside the official container environment (338 tests, 0 skips)
docker run --rm -v $(pwd):/workspace -w /workspace -e UV_PROJECT_ENVIRONMENT=/tmp/venv document-builder:0.1.0 uv run pytest -v

# Run the complete release validation script (testing Caddy HTTPS, isolation, fonts, cleanup)
python3 scripts/release_validation.py
```

- **Compatibility Profiles**: Every template package in `templates/` must have corresponding test profiles under `tests/compatibility/profiles/<template_id>/` (`minimal.yaml`, `normal.yaml`, `edge.yaml`).
- **Synthetic Test Data**: Compatibility fixtures must use realistic but strictly fictional or synthetic test data.

---

## 4. Code Formatting and Diff Hygiene

- Ensure clean diffs without whitespace errors or trailing spaces:
  ```bash
  git diff --check
  ```
- Keep changes minimal and focused. Avoid broad refactoring or reformatting outside the scope of your change.

---

## 5. Pull Requests

- When submitting a pull request, clearly describe:
  1. What behavior or feature was changed or added.
  2. How architectural boundaries and declarative template rules are respected.
  3. The test coverage added or verified.
- Ensure that the repository's automated validation passes without warnings or failures.

---

## 6. License and Contribution Terms

Unless explicitly stated otherwise, contributions intentionally submitted for inclusion in Document Builder are provided under the [Apache License 2.0](LICENSE), consistent with Section 5 of that license.
