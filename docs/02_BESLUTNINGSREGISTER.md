# Godkendt beslutningsregister

Dette dokument indeholder kun de endelige, gældende beslutninger. Historiske mellemkonklusioner og superseded research-formuleringer er udeladt.

1. **MVP:** Guided generator for alle 21 templates; intet permanent dokumentbibliotek.
2. **Adgang:** Offentligt internet, ingen login/konti, samme generatorrettighed for alle.
3. **Templates:** Filbaserede TemplatePackages; YAML + DOCX + assets; teknisk administrator; Git-versionering; auto-discovery.
4. **Domæne:** TemplatePackage → GenerationSession → GeneratedArtifact. Ingen permanent Document/Revision/User model.
5. **UX:** Kortforside → intro → ét wizard-trin ad gangen → kontrol → HTML-preview → ret → generér.
6. **Stack:** Python core; FastAPI + Jinja2 + HTMX webadapter; ingen SPA; core UI-uafhængig.
7. **Schema:** Deklarativ YAML med stabile IDs, låste field primitives, validation, simple conditions, static defaults, repeaters og privacy controls.
8. **Persistence:** Ingen database; GenerationSession i RAM; 60 min inactivity-TTL; ingen browser payload storage.
9. **Rendering:** DOCX via docxtpl er autoritativt; PDF afledes via LibreOffice; sikker escaping; hard failure ved kontraktbrud.
10. **Temp-data:** Artifacts slettes efter levering og senest efter 10 min cleanup.
11. **Drift:** Docker Compose; Caddy foran app; HTTPS; read-only templates; versionsmærkede images; simpel rollback.
12. **Backup:** Templates/config/secrets/Git; aldrig sessions eller genererede dokumenter.
13. **Konvertering:** HIF-01/02/07 først; derefter bølge B og C; ingen specialkode; kun konkrete generic gaps må udvide motoren.
14. **Validering:** Static schema + DOCX binding + minimal/normal/edge + security/privacy + PDF + manuel visual acceptance + fuld regression.
15. **Handoff:** Ingen åbne wayfinding-beslutninger; implementation kan begynde mod den kanoniske specifikation.
