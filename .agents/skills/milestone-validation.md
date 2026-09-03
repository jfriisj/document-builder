---
name: milestone-validation
description: Run the reusable final validation protocol for a Hashøj IF Dokumentbygger milestone without staging or committing changes.
---

Follow `AGENTS.md` as the workspace operating contract.

This skill validates the current milestone working tree.

Do not run `git add`.
Do not commit.
Do not push.

Procedure:

1. Inspect:

       git status --short

2. Review changed-file scope and confirm it matches the assigned milestone.

3. Run:

       uv run pytest -v

4. Run:

       git diff --check

5. If template or generic-engine work occurred, run a genericity search against
   `src/hashoej_document_builder/` for relevant HIF IDs/document names.

6. Confirm generated artifacts are not tracked, including:
   - generated DOCX
   - generated PDF
   - screenshots
   - raw XML
   - LibreOffice profiles
   - review bundles
   - scratch files

7. Report exact:
   - passed tests
   - skipped tests
   - warnings
   - failures

8. Report `git diff --check` honestly.

9. Report genericity result where relevant.

10. Report deviations and remaining blockers.

Return only:

GIT STATUS
CHANGED SCOPE
TESTS
GIT DIFF CHECK
GENERICITY
UNWANTED TRACKED ARTIFACTS
DEVIATIONS
BLOCKERS
RESULT
