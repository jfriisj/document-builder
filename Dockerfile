# Canonical production Dockerfile for Document Builder
FROM python:3.11-slim

# Prevent python from buffering stdout/stderr and writing pyc to disk
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

# Install LibreOffice headless, metrics-compatible fonts, and font utilities
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libreoffice-writer-nogui \
        fonts-crosextra-carlito \
        poppler-utils && \
    rm -rf /var/lib/apt/lists/*


# Configure deterministic fontconfig aliases for Aptos and Aptos Display
COPY docker/30-aptos-aliases.conf /etc/fonts/conf.d/30-aptos-aliases.conf
RUN fc-cache -f

# Create dedicated non-root runtime user with writable home directory
RUN groupadd -g 10001 app && \
    useradd -u 10001 -g app -s /bin/bash -m app

WORKDIR /app

# Install pinned uv binary from official image
COPY --from=ghcr.io/astral-sh/uv:0.12.9 /uv /bin/uv

# Copy dependency definition files first for layer caching
COPY pyproject.toml uv.lock README.md ./

# Deterministically install production dependencies into /app/.venv
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source code and install project into venv
COPY src/ ./src/
RUN uv sync --frozen --no-dev && \
    chown -R app:app /app

# Switch to non-root runtime user
USER app

# Internal port only; never published directly to the host
EXPOSE 8000

# Run single uvicorn worker without reload, enabling proxy headers from reverse proxy
CMD ["uvicorn", "hashoej_document_builder.web.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips=*"]
