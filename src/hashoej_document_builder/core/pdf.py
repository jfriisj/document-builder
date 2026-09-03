"""PDF conversion pipeline using LibreOffice headless."""

from __future__ import annotations

import logging
from pathlib import Path
import shutil
import subprocess
import tempfile

from hashoej_document_builder.core.errors import (
    PDFConversionError,
    PDFConversionUnavailableError,
)

logger = logging.getLogger(__name__)


def convert_docx_to_pdf(
    docx_path: Path | str,
    output_dir: Path | str,
    timeout_seconds: float = 30.0,
    soffice_cmd: str | None = None,
) -> Path:
    """Convert a rendered DOCX file to PDF using LibreOffice headless.

    Uses an isolated temporary LibreOffice user profile per conversion to ensure safe concurrency.

    Args:
        docx_path: Path to the successfully rendered source DOCX.
        output_dir: Directory where the output PDF should be written.
        timeout_seconds: Maximum allowed conversion execution time.
        soffice_cmd: Optional explicit path to the soffice/libreoffice binary.

    Returns:
        Path to the successfully converted non-empty PDF file.

    Raises:
        PDFConversionUnavailableError: If LibreOffice is not installed/found.
        PDFConversionError: If conversion fails, times out, or produces an invalid/empty PDF.
    """
    input_path = Path(docx_path).resolve()
    out_dir = Path(output_dir).resolve()
    expected_pdf = out_dir / f"{input_path.stem}.pdf"

    if not input_path.is_file():
        raise PDFConversionError(f"Input DOCX file not found: {input_path}")

    out_dir.mkdir(parents=True, exist_ok=True)

    cmd = soffice_cmd or shutil.which("soffice") or shutil.which("libreoffice")
    if not cmd:
        raise PDFConversionUnavailableError(
            "LibreOffice executable (soffice/libreoffice) is not installed or available in PATH."
        )

    # Clean any pre-existing stale expected PDF before invoking converter
    if expected_pdf.exists():
        expected_pdf.unlink(missing_ok=True)

    # Use an isolated, temporary, per-conversion user profile
    with tempfile.TemporaryDirectory(prefix="lo_profile_") as profile_dir:
        profile_uri = Path(profile_dir).resolve().as_uri()

        args = [
            cmd,
            f"-env:UserInstallation={profile_uri}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(out_dir),
            str(input_path),
        ]

        try:
            proc = subprocess.run(
                args,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        except FileNotFoundError as exc:
            if expected_pdf.exists():
                expected_pdf.unlink(missing_ok=True)
            raise PDFConversionUnavailableError(
                f"LibreOffice executable not found during invocation: {cmd}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            if expected_pdf.exists():
                expected_pdf.unlink(missing_ok=True)
            logger.error("LibreOffice PDF conversion timed out after %s seconds", timeout_seconds)
            raise PDFConversionError(
                f"PDF conversion timed out after {timeout_seconds} seconds."
            ) from exc
        except OSError as exc:
            if expected_pdf.exists():
                expected_pdf.unlink(missing_ok=True)
            logger.error("LibreOffice subprocess execution failed: %s", type(exc).__name__)
            raise PDFConversionError(f"Failed to execute LibreOffice converter: {exc}") from exc

        if proc.returncode != 0:
            if expected_pdf.exists():
                expected_pdf.unlink(missing_ok=True)
            err_msg = proc.stderr.decode("utf-8", errors="replace").strip()
            logger.error("LibreOffice conversion exited with returncode %s", proc.returncode)
            raise PDFConversionError(
                f"LibreOffice PDF conversion failed with exit code {proc.returncode}: {err_msg}"
            )

        if not expected_pdf.is_file():
            raise PDFConversionError(
                f"PDF conversion completed but output file was not found: {expected_pdf.name}"
            )

        if expected_pdf.stat().st_size == 0:
            expected_pdf.unlink(missing_ok=True)
            raise PDFConversionError("PDF conversion produced an empty (0-byte) file.")

        return expected_pdf
