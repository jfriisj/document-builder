---
name: compatibility-validation
description: Validate real TemplatePackages, compatibility profiles, DOCX bindings, rendering, and the HIF compatibility regression set.
---

Follow `AGENTS.md` as the workspace operating contract.

This skill is validation-only.

Do not modify source files unless the parent/orchestrating agent explicitly asks
for a fix after validation.

Validation procedure:

1. Discover the real TemplatePackages in the workspace.
2. Validate each `template.yaml` against the existing schema.
3. Validate each `document.docx` with the existing DOCX binding validator.
4. Validate compatibility profiles:
   - `minimal.yaml`
   - `normal.yaml`
   - `edge.yaml`
5. Build render contexts from validated profile data.
6. Render representative DOCX outputs.
7. Re-open rendered DOCX files and verify they are structurally valid.
8. Where compatibility tests define structural expectations, verify:
   - expected table counts
   - repeater-generated rows
   - representative source data
9. Explicitly verify the approved compatibility regression set:
   - HIF-01 Rollebeskrivelse
   - HIF-02 Opgavekort
   - HIF-07 Arrangementsskabelon
10. Confirm their approved repeater baseline remains:
    - HIF-01: 3
    - HIF-02: 4
    - HIF-07: 6
11. Run the relevant compatibility tests.
12. If LibreOffice is available and PDF compatibility is in scope, perform real
    conversion rather than simulating success.

Report only:

SCOPE
TEMPLATES CHECKED
PROFILE MATRIX
DOCX BINDING
DOCX RENDERING
STRUCTURAL CHECKS
HIF-01 REGRESSION
HIF-02 REGRESSION
HIF-07 REGRESSION
PDF
BLOCKERS
RESULT

Use concise PASS/FAIL totals.

Do not return complete test logs unless a failure requires the relevant excerpt.
