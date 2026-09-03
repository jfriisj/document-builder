# Security Policy

## Reporting Security Issues

We take the security of Document Builder seriously.

If you believe you have discovered a vulnerability or potential security issue that exposes exploitable details, please **do not** open a public issue or discussion in the public repository tracker.

### Reporting Channel

> **TODO BEFORE PUBLICATION: configure a private security reporting channel.**

This repository must not be made public until a private security reporting channel has been configured and documented here.

Until a dedicated private reporting channel is configured and documented:
- Do not post exploitable vulnerability details in publicly visible issues.

## Security Design & Data Protection Principles

Document Builder is architected with strict data minimization principles:
- **No Database**: Generation sessions exist solely in transient memory (RAM) and expire automatically after 60 minutes of inactivity.
- **Opaque Session Tokens**: Cookies contain only random opaque identifiers (`document_builder_session_id`) marked `HttpOnly`, `SameSite=Lax`, and `Secure` over HTTPS. Form values and personal data are never stored in cookies.
- **Transient Artifact Storage**: Generated files are stored in a non-public temporary folder and purged immediately following download or after 10 minutes by a background stale-purging routine.
- **No In-browser Persistence**: Client-side storage (`localStorage`, `sessionStorage`) and HTMX history caches are explicitly disabled.
- **Strict Privacy Gates**: High-sensitivity templates (such as incident and injury reports) remain disabled by default (`enabled: false`) under explicit privacy and legal activation gates.
