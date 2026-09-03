"""Generate canonical PDF and DOCX review artifacts for Milestone 7 release review."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import yaml

from hashoej_document_builder.core.discovery import load_template_package
from hashoej_document_builder.core.pdf import convert_docx_to_pdf
from hashoej_document_builder.core.rendering import build_render_context, render_docx
from hashoej_document_builder.core.validation import validate_all_steps_values

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = WORKSPACE_ROOT / "templates"
PROFILES_DIR = WORKSPACE_ROOT / "tests" / "compatibility" / "profiles"

ALL_TEMPLATES = [
    "hif-01-role",
    "hif-02-task",
    "hif-03-handover",
    "hif-04-annual-cycle",
    "hif-05-contact",
    "hif-06-contract",
    "hif-07-event",
    "hif-08-project",
    "hif-09-minutes",
    "hif-10-decision-log",
    "hif-11-action-list",
    "hif-12-volunteer-shift",
    "hif-13-volunteer-onboarding",
    "hif-14-key-access",
    "hif-15-inventory",
    "hif-16-maintenance",
    "hif-17-incident",
    "hif-18-purchase",
    "hif-19-sponsor",
    "hif-20-communication",
    "hif-21-gdpr",
]

COMPATIBILITY_SET = ["hif-01-role", "hif-02-task", "hif-07-event"]


def generate_artifacts(output_dir: Path) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_entries: list[dict] = []

    tasks: list[tuple[str, str]] = []
    # 1. Normal profile for all 21 templates
    for tid in ALL_TEMPLATES:
        tasks.append((tid, "normal"))

    # 2. Minimal and Edge profiles for compatibility set
    for tid in COMPATIBILITY_SET:
        tasks.append((tid, "minimal"))
        tasks.append((tid, "edge"))

    print(f"Generating {len(tasks)} review document pairs in {output_dir}...")

    soffice_cmd = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice_cmd:
        print("ERROR: LibreOffice (soffice) not found in PATH.", file=sys.stderr)
        sys.exit(1)

    for template_id, profile_name in tasks:
        pkg_dir = TEMPLATES_DIR / template_id
        profile_file = PROFILES_DIR / template_id / f"{profile_name}.yaml"

        pkg = load_template_package(pkg_dir)
        raw_profile = yaml.safe_load(profile_file.read_text(encoding="utf-8"))

        val_res = validate_all_steps_values(pkg.form_definition, raw_profile)
        if not val_res.is_valid:
            raise RuntimeError(f"Validation failed for {template_id} ({profile_name}): {val_res.errors}")

        render_ctx = build_render_context(pkg.form_definition, val_res.coerced_values)

        file_prefix = f"{template_id}_{profile_name}"
        docx_path = output_dir / f"{file_prefix}.docx"
        render_docx(pkg.document_template, render_ctx, docx_path)

        pdf_path = convert_docx_to_pdf(docx_path, output_dir, soffice_cmd=soffice_cmd)

        status_tag = "ENABLED" if pkg.enabled else "DISABLED / NOT PUBLIC / PRIVACY-GATED"
        verdict = "SUCCESS" if pdf_path.is_file() and pdf_path.stat().st_size > 0 else "FAILED"

        entry = {
            "template_id": template_id,
            "enabled": pkg.enabled,
            "status": status_tag,
            "profile": profile_name,
            "docx_path": str(docx_path),
            "pdf_path": str(pdf_path),
            "docx_size_bytes": docx_path.stat().st_size,
            "pdf_size_bytes": pdf_path.stat().st_size,
            "verdict": verdict,
        }
        manifest_entries.append(entry)
        print(f"  [{verdict}] {template_id} ({profile_name}): DOCX={entry['docx_size_bytes']}b, PDF={entry['pdf_size_bytes']}b [{status_tag}]")

    # Write manifest files
    manifest_json = output_dir / "manifest.json"
    manifest_json.write_text(json.dumps(manifest_entries, indent=2, ensure_ascii=False), encoding="utf-8")

    manifest_txt = output_dir / "manifest.txt"
    lines = [
        "================================================================================",
        "DOCUMENT BUILDER - MILESTONE 7 PDF/DOCX REVIEW ARTIFACTS MANIFEST",
        "================================================================================",
        f"Total documents: {len(manifest_entries)}",
        f"Target directory: {output_dir}",
        "",
        f"{'Template ID':<28} {'Profile':<10} {'Enabled':<10} {'DOCX Size':<12} {'PDF Size':<12} {'Verdict':<10}",
        "-" * 86,
    ]
    for e in manifest_entries:
        lines.append(
            f"{e['template_id']:<28} {e['profile']:<10} {str(e['enabled']):<10} {e['docx_size_bytes']:<12} {e['pdf_size_bytes']:<12} {e['verdict']:<10}"
        )
    lines.append("-" * 86)
    lines.append("NOTE: HIF-17 is DISABLED / NOT PUBLIC / PRIVACY-GATED and not exposed publicly.")
    manifest_txt.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nManifest written to {manifest_json} and {manifest_txt}")

    # Generate runtime-fonts.txt
    fonts_txt = output_dir / "runtime-fonts.txt"
    font_lines = [
        "================================================================================",
        "RUNTIME FONT RESOLUTION AND PDF EMBEDDING AUDIT",
        "================================================================================",
        "",
        "--- fc-match Aptos ---",
        subprocess.run(["fc-match", "Aptos"], capture_output=True, text=True).stdout.strip(),
        "",
        '--- fc-match "Aptos Display" ---',
        subprocess.run(["fc-match", "Aptos Display"], capture_output=True, text=True).stdout.strip(),
        "",
    ]
    for tid in ["hif-01-role", "hif-07-event", "hif-21-gdpr"]:
        sample_pdf = output_dir / f"{tid}_normal.pdf"
        font_lines.append(f"--- pdffonts {sample_pdf.name} ---")
        if sample_pdf.exists() and shutil.which("pdffonts"):
            res = subprocess.run(["pdffonts", str(sample_pdf)], capture_output=True, text=True)
            font_lines.append(res.stdout.strip())
        else:
            font_lines.append("pdffonts not available or PDF not found")
        font_lines.append("")

    fonts_txt.write_text("\n".join(font_lines) + "\n", encoding="utf-8")
    print(f"Runtime font audit written to {fonts_txt}")

    return manifest_entries


if __name__ == "__main__":
    out_dir = Path("/tmp/m7-pdf-review")
    generate_artifacts(out_dir)

