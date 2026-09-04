# Security Policy

## Reporting Security Issues

We take the security of Document Builder seriously.

If you believe you have discovered a vulnerability or potential security issue that exposes exploitable details, please **do not** open a public issue or discussion containing vulnerability details.

### Private Vulnerability Reporting

Document Builder uses GitHub Private Vulnerability Reporting as the preferred security reporting channel.

When private vulnerability reporting is enabled for this repository:

1. Open the repository on GitHub.
2. Select **Security**.
3. Select **Report a vulnerability**.
4. Submit the vulnerability details through GitHub's private advisory form.

Reports submitted through this mechanism are visible privately to the repository maintainers.

Do not disclose exploitable vulnerability details through public issues, pull requests, discussions, or other public repository content.

### Publication Requirement

GitHub Private Vulnerability Reporting can only be enabled after a repository is public.

For that reason, publication of this repository follows this controlled sequence:

1. Keep the repository private while preparing and auditing the release.
2. Change repository visibility to public.
3. Immediately enable GitHub Private Vulnerability Reporting.
4. Verify that private vulnerability reporting is enabled.
5. Only then consider the public release complete and announce or distribute the repository.

If private vulnerability reporting cannot be enabled or verified during publication, the repository should be returned to private visibility until the problem has been resolved.

## Security Design & Data Protection Principles

Document Builder is architected with strict data minimization principles:

- **No Database**: Generation sessions exist solely in transient memory (RAM) and expire automatically after 60 minutes of inactivity.
- **Opaque Session Tokens**: Cookies contain only random opaque identifiers (`document_builder_session_id`) marked `HttpOnly`, `SameSite=Lax`, and `Secure` over HTTPS. Form values and personal data are never stored in cookies.
- **Transient Artifact Storage**: Generated files are stored in a non-public temporary folder and purged immediately following download or after 10 minutes by a background stale-purging routine.
- **No In-browser Persistence**: Client-side storage (`localStorage`, `sessionStorage`) and HTMX history caches are explicitly disabled.
- **Strict Privacy Gates**: High-sensitivity templates (such as incident and injury reports) remain disabled by default (`enabled: false`) under explicit privacy and legal activation gates.
