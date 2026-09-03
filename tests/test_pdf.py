from pathlib import Path
import shutil
import subprocess
from unittest.mock import MagicMock, patch
from urllib.parse import unquote, urlparse
import docx
import pytest

from hashoej_document_builder.core.errors import (
    PDFConversionError,
    PDFConversionUnavailableError,
)
from hashoej_document_builder.core.pdf import convert_docx_to_pdf


def _make_dummy_docx(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = docx.Document()
    doc.add_paragraph("Test indhold")
    doc.save(str(path))
    return path


def _uri_to_path(uri: str) -> Path:
    parsed = urlparse(uri)
    return Path(unquote(parsed.path))


def test_pdf_conversion_missing_input_docx(tmp_path: Path) -> None:
    with pytest.raises(PDFConversionError, match="Input DOCX file not found"):
        convert_docx_to_pdf(tmp_path / "non_existent.docx", tmp_path / "out")


def test_pdf_conversion_missing_executable_raises_unavailable(tmp_path: Path) -> None:
    docx_path = _make_dummy_docx(tmp_path / "doc.docx")
    with patch("shutil.which", return_value=None):
        with pytest.raises(PDFConversionUnavailableError, match="LibreOffice executable"):
            convert_docx_to_pdf(docx_path, tmp_path / "out", soffice_cmd=None)


def test_pdf_conversion_explicit_nonexistent_executable_raises_unavailable(tmp_path: Path) -> None:
    docx_path = _make_dummy_docx(tmp_path / "doc.docx")
    with pytest.raises(PDFConversionUnavailableError, match="LibreOffice executable not found"):
        convert_docx_to_pdf(docx_path, tmp_path / "out", soffice_cmd="/non/existent/path/to/soffice")


def test_pdf_conversion_subprocess_filenotfound_raises_unavailable(tmp_path: Path) -> None:
    docx_path = _make_dummy_docx(tmp_path / "doc.docx")
    out_dir = tmp_path / "out"
    with patch("subprocess.run", side_effect=FileNotFoundError("Executable vanished")):
        with patch("pathlib.Path.is_file", return_value=True):
            with pytest.raises(PDFConversionUnavailableError, match="LibreOffice executable not found during invocation"):
                convert_docx_to_pdf(docx_path, out_dir, soffice_cmd="/usr/bin/soffice")


def test_pdf_conversion_isolated_user_profile_and_stale_pdf_cleanup(tmp_path: Path) -> None:
    """Verify that LibreOffice is invoked with an isolated user profile and stale PDFs are removed."""
    docx_path = _make_dummy_docx(tmp_path / "test_doc.docx")
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    expected_pdf = out_dir / "test_doc.pdf"

    # Write a pre-existing stale PDF to verify it gets removed before conversion
    expected_pdf.write_bytes(b"stale old pdf content")

    captured_profile_dirs: list[Path] = []

    def fake_subprocess_run(args, **kwargs):
        assert kwargs.get("shell") is False
        assert kwargs.get("capture_output") is True
        assert args[0] == "/usr/bin/soffice"

        # Find and verify -env:UserInstallation argument
        profile_arg = next(a for a in args if a.startswith("-env:UserInstallation="))
        profile_uri = profile_arg.split("=", 1)[1]
        assert profile_uri.startswith("file://")

        profile_path = _uri_to_path(profile_uri)
        # Profile directory must exist and be writable while subprocess runs
        assert profile_path.is_dir()
        captured_profile_dirs.append(profile_path)

        assert "--headless" in args
        assert "--convert-to" in args
        assert "pdf" in args
        assert "--outdir" in args

        # Write fresh valid PDF
        expected_pdf.write_bytes(b"%PDF-1.4 fresh mock content")
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        return mock_proc

    with patch("subprocess.run", side_effect=fake_subprocess_run):
        result = convert_docx_to_pdf(docx_path, out_dir, soffice_cmd="/usr/bin/soffice")
        assert result == expected_pdf
        assert result.read_bytes().startswith(b"%PDF-1.4")

    # Profile directory must have been cleaned up after conversion
    assert len(captured_profile_dirs) == 1
    assert not captured_profile_dirs[0].exists()


def test_pdf_conversion_concurrency_isolation_unique_profiles(tmp_path: Path) -> None:
    """Two independent conversions must use distinct profile directories and cleanup both."""
    docx_a = _make_dummy_docx(tmp_path / "doc_a.docx")
    docx_b = _make_dummy_docx(tmp_path / "doc_b.docx")
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    captured_uris: list[str] = []
    captured_paths: list[Path] = []

    def fake_run(args, **kwargs):
        profile_arg = next(a for a in args if a.startswith("-env:UserInstallation="))
        uri = profile_arg.split("=", 1)[1]
        captured_uris.append(uri)
        path = _uri_to_path(uri)
        captured_paths.append(path)

        # Write expected pdf
        input_name = Path(args[-1]).stem
        (out_dir / f"{input_name}.pdf").write_bytes(b"%PDF-1.4 ok")
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        return mock_proc

    with patch("subprocess.run", side_effect=fake_run):
        convert_docx_to_pdf(docx_a, out_dir, soffice_cmd="/usr/bin/soffice")
        convert_docx_to_pdf(docx_b, out_dir, soffice_cmd="/usr/bin/soffice")

    assert len(captured_uris) == 2
    assert captured_uris[0] != captured_uris[1]
    assert not captured_paths[0].exists()
    assert not captured_paths[1].exists()


def test_pdf_conversion_timeout_handling_and_profile_cleanup(tmp_path: Path) -> None:
    docx_path = _make_dummy_docx(tmp_path / "doc.docx")
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    expected_pdf = out_dir / "doc.pdf"

    captured_paths: list[Path] = []

    def fake_timeout(args, **kwargs):
        profile_arg = next(a for a in args if a.startswith("-env:UserInstallation="))
        captured_paths.append(_uri_to_path(profile_arg.split("=", 1)[1]))
        expected_pdf.write_bytes(b"%PDF partial corrupt")
        raise subprocess.TimeoutExpired(cmd="soffice", timeout=5.0)

    with patch("subprocess.run", side_effect=fake_timeout):
        with pytest.raises(PDFConversionError, match="PDF conversion timed out"):
            convert_docx_to_pdf(docx_path, out_dir, timeout_seconds=5.0, soffice_cmd="/usr/bin/soffice")

    # Both partial PDF and isolated profile directory must have been cleaned up
    assert not expected_pdf.exists()
    assert len(captured_paths) == 1
    assert not captured_paths[0].exists()


def test_pdf_conversion_nonzero_exit_code_and_profile_cleanup(tmp_path: Path) -> None:
    docx_path = _make_dummy_docx(tmp_path / "doc.docx")
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    expected_pdf = out_dir / "doc.pdf"

    captured_paths: list[Path] = []

    def fake_fail(args, **kwargs):
        profile_arg = next(a for a in args if a.startswith("-env:UserInstallation="))
        captured_paths.append(_uri_to_path(profile_arg.split("=", 1)[1]))
        expected_pdf.write_bytes(b"%PDF partial")
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stderr = b"Fatal conversion error"
        return mock_proc

    with patch("subprocess.run", side_effect=fake_fail):
        with pytest.raises(PDFConversionError, match="failed with exit code 1"):
            convert_docx_to_pdf(docx_path, out_dir, soffice_cmd="/usr/bin/soffice")

    assert not expected_pdf.exists()
    assert len(captured_paths) == 1
    assert not captured_paths[0].exists()


def test_pdf_conversion_output_file_not_created(tmp_path: Path) -> None:
    docx_path = _make_dummy_docx(tmp_path / "doc.docx")
    out_dir = tmp_path / "out"

    mock_proc = MagicMock()
    mock_proc.returncode = 0

    with patch("subprocess.run", return_value=mock_proc):
        with pytest.raises(PDFConversionError, match="output file was not found"):
            convert_docx_to_pdf(docx_path, out_dir, soffice_cmd="/usr/bin/soffice")


def test_pdf_conversion_empty_pdf_rejected(tmp_path: Path) -> None:
    docx_path = _make_dummy_docx(tmp_path / "doc.docx")
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    expected_pdf = out_dir / "doc.pdf"

    def fake_subprocess_creates_empty(args, **kwargs):
        expected_pdf.write_bytes(b"")
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        return mock_proc

    with patch("subprocess.run", side_effect=fake_subprocess_creates_empty):
        with pytest.raises(PDFConversionError, match="empty .* file"):
            convert_docx_to_pdf(docx_path, out_dir, soffice_cmd="/usr/bin/soffice")


def test_real_libreoffice_integration(tmp_path: Path) -> None:
    """Real LibreOffice conversion test. Skipped if soffice/libreoffice is not installed in the test environment."""
    soffice_cmd = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice_cmd:
        pytest.skip("LibreOffice (soffice/libreoffice) executable is not installed locally.")

    docx_path = _make_dummy_docx(tmp_path / "real_doc.docx")
    out_dir = tmp_path / "real_out"

    pdf_path = convert_docx_to_pdf(docx_path, out_dir, soffice_cmd=soffice_cmd)
    assert pdf_path.is_file()
    assert pdf_path.stat().st_size > 0
    content = pdf_path.read_bytes()
    assert content.startswith(b"%PDF")
