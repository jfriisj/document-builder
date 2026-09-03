# Third-Party Notices and Informational Inventory

Document Builder integrates or interfaces with various third-party open-source software and components at runtime. This document provides an informational inventory of these components. This file does not replace, alter, or relicense any upstream licenses. Upstream licenses and copyright notices are provided by their respective authors and distribution packages.

---

## 1. Runtime Components and External Software

### Carlito Font
- **Purpose**: Used at container runtime as a deterministic metric-compatible font substitute for Aptos and Aptos Display during LibreOffice PDF conversion (`docker/30-aptos-aliases.conf`).
- **License**: SIL Open Font License, Version 1.1 (OFL-1.1).
- **Source / Packaging**: Font binary files are not tracked or distributed directly in this Git repository. Instead, they are obtained via the operating-system package manager (`fonts-crosextra-carlito`) during the container image build.
- **Notice**: Carlito is not licensed under Apache License 2.0 and is not relicensed by Document Builder. Redistribution of the container image must comply with the terms of the SIL Open Font License 1.1.

### LibreOffice
- **Purpose**: Headless conversion of rendered DOCX documents to PDF format (`soffice --headless --convert-to pdf`).
- **License**: Mozilla Public License 2.0 (MPL-2.0) and additional open-source licenses.
- **Source / Packaging**: Installed at container build time via Debian operating-system packages (`libreoffice-writer-nogui`).
- **Notice**: LibreOffice is made available under Mozilla Public License 2.0 and includes software under a variety of additional open-source licenses which may differ between versions/distributions. Document Builder does not relicense LibreOffice. Redistributors of container images should inspect the specific copyright and license notices provided within the installed LibreOffice distribution.

### Caddy
- **Purpose**: Reverse proxy, network isolation enforcement, and automated TLS termination.
- **License**: Apache License 2.0.
- **Source / Packaging**: Utilized as an upstream, unmodified official container image (`caddy:2-alpine`).
- **Notice**: Caddy remains a distinct third-party component governed by its own upstream Apache-2.0 licensing and trademark terms.

### Base Images and Operating System Packages
- **Base Image**: Python slim base image (`python:3.11-slim`, Debian GNU/Linux).
- **Packaging**: Container builds install Debian operating-system packages (including fontconfig, LibreOffice headless, and Carlito).
- **Notice**: Copyright, license notices, and full texts for Debian packages are provided by Debian and their respective authors within their system package documentation.

---

## 2. Python Direct Dependencies

Document Builder declares direct dependencies in [`pyproject.toml`](pyproject.toml).

### Dependency Inventory

| Package | Direct / Dev | Upstream License | Purpose |
| :--- | :--- | :--- | :--- |
| `docxtpl` | Direct | LGPL-2.1-only | DOCX template rendering with Jinja tags |
| `fastapi` | Direct | MIT | Web application framework and ASGI routing |
| `jinja2` | Direct | BSD-3-Clause | Templating engine for HTML forms and docxtpl expressions |
| `pydantic` | Direct | MIT | Data models, settings, and declarative schema validation |
| `python-docx` | Direct | MIT | Microsoft Word DOCX file manipulation |
| `python-multipart` | Direct | Apache-2.0 | Form data parsing for HTTP requests |
| `pyyaml` | Direct | MIT | YAML parsing for template package definitions |
| `uvicorn` | Direct | BSD-3-Clause | ASGI web server implementation |
| `httpx` | Dev | BSD-3-Clause | HTTP test client library |
| `pytest` | Dev | MIT | Test framework |
| `pytest-cov` | Dev | MIT | Test coverage reporting |

### Vendoring Status
- **Zero Vendored Code**: Document Builder does not vendor, copy, or bundle any third-party Python library source code or compiled wheels within this repository.
- **Upstream Licensing**: All Python dependencies are downloaded dynamically during environment setup or container image creation from the Python Package Index (PyPI). Each dependency remains subject to its own upstream license.
