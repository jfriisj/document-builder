# Document Builder — Agent Operating Contract

## Project

Document Builder is a public, login-free guided document generator. This repository bundles the Hashøj IF reference template pack as the reference implementation.

Primary stack:

- Python
- FastAPI
- Jinja2
- HTMX
- docxtpl
- LibreOffice

Template behaviour is declarative through YAML + DOCX.

## Authoritative documentation

Consult the repository documentation relevant to the task:

- `docs/01_IMPLEMENTATIONSSPECIFIKATION.md`
- `docs/03_KONVERTERINGSPLAN_21_TEMPLATES.md`
- `docs/04_ACCEPTANCE_OG_KOMPATIBILITETSGATES.md`
- `docs/DOCX_TEMPLATE_AUTHORING.md`

The implementation specification takes precedence for architecture.

The actual HIF Word references take precedence for source-document content,
structure, fields, tables, metadata and visual hierarchy.

## Architecture boundaries

- Core must remain independent of FastAPI, HTMX and web concerns.
- Template-specific behaviour belongs in:
  - `template.yaml`
  - `document.docx`
  - `assets/`
  - compatibility profile data
- No document-specific Python.
- No branching on HIF template IDs in core, web or runtime code.
- No per-document renderers, services or validators.
- No database, accounts, permanent document history or persistent sessions
  unless an explicitly approved future milestone changes the architecture.

## Template fidelity

Actual Word references are authoritative for:

- document purpose
- sections and section order
- tables
- repeated structures
- static labels
- metadata
- headers and footers
- important page/layout structure
- visual hierarchy

Technical Word implementation details may be simplified.

Domain information structure may not be simplified away.

A genuine repeated source table should normally be represented by a generic
YAML repeater.

Never redesign a source document merely to make implementation easier.

## Generic engine rule

Always attempt to express a real source requirement using the existing generic
schema and DOCX grammar first.

Do not extend core, schema or rendering proactively.

If the existing engine genuinely cannot express a source requirement, report:

ENGINE GAP CANDIDATE

Source:
Exact requirement:
Existing capability attempted:
Why it cannot express the requirement:
Smallest generic extension:
Why it is reusable:

Only the primary/orchestrating agent may authorize integration of an engine
change.

Template subagents may report engine gaps but must not independently modify
generic engine code.

## Existing template primitives

Supported primitives:

- `text`
- `textarea`
- `number`
- `date`
- `select`
- `radio`
- `checkbox`
- `multiselect`
- `repeater`
- `info`

Supported text formats:

- `email`
- `tel`
- `url`

Use the implementation and authoring documentation for detailed validation
rules.

## DOCX rules

- DOCX owns document layout.
- User input is data only.
- Use the existing validated docxtpl grammar.
- Repeated table rows use structural row control tags.
- All DOCX templates must pass the existing binding validator.

Do not add:

- custom filters
- macros
- imports
- arbitrary expressions
- Python functions
- document-specific helpers

## Privacy

- Sessions are transient RAM-only application state.
- Do not use real personal data in tests or compatibility profiles.
- Templates that collect personal/contact references must provide contextual:
  - `type: info`
  - `variant: privacy`
- Privacy information should explain:
  - why the information is needed for that document
  - that Dokumentbyggeren processes it during the active session
  - that the application does not permanently store it
- Do not invent consent, acknowledgement, legal basis or legal conclusions.

## Compatibility regression set

The approved compatibility regression set is:

- HIF-01 Rollebeskrivelse
- HIF-02 Opgavekort
- HIF-07 Arrangementsskabelon

Approved repeater baseline:

- HIF-01: 3 repeaters
- HIF-02: 4 repeaters
- HIF-07: 6 repeaters

Future generic changes must not regress these templates.

## Development workflow

Use:

explore
→ plan
→ implement
→ validate
→ independent review where appropriate

For complex work:

- use focused subagents to preserve parent context
- give subagents only the minimum source/specification context required
- return concise structured findings
- do not return raw XML, full file dumps, verbose reasoning transcripts or
  complete test logs unless specifically required

The primary agent remains responsible for integration and final verification.

Never trust a subagent completion report without inspecting resulting files,
diffs and relevant outputs.

## Git rules

- Never commit unless the user explicitly instructs you to commit.
- Never push unless explicitly instructed.
- Do not run `git add` automatically as part of implementation completion.
- Generated DOCX/PDF review files, screenshots, XML dumps, temporary
  LibreOffice profiles, analysis bundles and scratch files must not be tracked.
- Finish implementation with the working-tree diff available for human review.

## Validation

Permanent baseline:

    uv run pytest -v
    git diff --check

Also run genericity checks whenever work touches templates or generic engine
behaviour.

Do not suppress warnings merely to make output cleaner.

## Completion reports

Keep completion reports concise.

Include:

- scope completed
- files changed
- engine gaps
- tests
- `git diff --check`
- genericity result where relevant
- deviations
- remaining blockers

Do not include hidden reasoning or lengthy work transcripts.

## High-risk personal-data activation gate

Templates that may collect special-category or otherwise high-risk personal
data require a separate explicit human privacy/legal review before activation.

Examples include, where applicable:

- injury or symptom information
- medical treatment or first-aid details
- health information
- sensitive incident details tied to identifiable persons
- other special-category or high-risk personal information

When such data are required by an authoritative source document:

- preserve the source requirement; do not silently remove it
- provide appropriate contextual privacy information
- do not invent consent, legal basis or legal conclusions
- report that a separate privacy/legal activation gate is required
- keep the TemplatePackage valid and testable
- keep `enabled: false` while that gate is unresolved
- ensure disabled templates are not exposed through the public template catalog

Only an explicit human decision may clear the activation gate and allow
`enabled: true`.
