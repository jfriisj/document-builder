---
title: "Lås implementationens handoff-specifikation"
state: closed
label: "wayfinder:grilling"
mode: "HITL"
parent: "Find vejen til Hashøj IF dokumentbyggeren"
claimed_by: "project team"
blocked_by:
  - "Afgræns MVP og definer succes"
  - "Definer brugere, adgang og trust boundary"
  - "Beslut hvordan templates oprettes og ændres"
  - "Modelér templates, dokumenter, revisioner og filer"
  - "Prototype den guidede dokumentrejse"
  - "Beslut template-schema og feltprimitiver"
  - "Beslut persistence, revisionering og recovery"
  - "Beslut dokumentrenderingens kontrakt"
  - "Beslut drift, backup og opdatering"
  - "Planlæg konvertering af de 21 Hashøj IF-skabeloner"
  - "Definer validering og kompatibilitetsgates"
---

# Lås implementationens handoff-specifikation

## Question

Er alle beslutninger, grænseflader, acceptance-kriterier og bevidste fravalg nu præcise nok til, at implementation kan begynde uden yderligere produkt- eller arkitekturwayfinding; og hvad er den endelige kontrakt, som implementeringen skal følge?

## Resolution

### Konklusion

Wayfinder-destinationen er nået.

Alle produkt-, domæne-, template-, UX-, persistence-, dokumentrenderings-, privacy/sikkerheds-, drifts-, konverterings- og valideringsbeslutninger, som er nødvendige for at begynde MVP-implementationen, er nu låst.

Der er ingen resterende punkter under `Not yet specified`.

Implementation må derfor begynde uden yderligere produkt- eller arkitekturwayfinding, så længe den følger den kanoniske implementationsspecifikation.

### Kanonisk handoff

Den endelige implementation skal følge disse hovedkontrakter:

- MVP er en offentlig, login-fri, guided dokumentgenerator for alle 21 Hashøj IF-dokumenttyper.
- Python er core/backend-sprog.
- Webadapteren er FastAPI + Jinja2 + HTMX med almindelig CSS og minimal vanilla JavaScript.
- Core må ikke afhænge af FastAPI/HTMX.
- YAML er source of truth for formular-definitionen.
- Hver dokumenttype er en filbaseret TemplatePackage med `template.yaml` + `document.docx` + eventuelle assets.
- Schemaet bruger de låste deklarative feltprimitiver og stabile field IDs.
- GenerationSession er transient, RAM-only, uden SQLite/database og med 60 minutters inactivity-TTL.
- Browseren bruger kun opaque teknisk session-id; ingen formularpayload i browser storage.
- DOCX er autoritativt dokumentlayout/output via docxtpl.
- PDF genereres fra DOCX via LibreOffice headless.
- GeneratedArtifacts er transient og slettes efter levering; stale artifacts ryddes senest efter 10 minutter.
- Produktion er én Docker Compose-stack med Caddy foran FastAPI.
- HTTPS er obligatorisk; kun Caddy eksponeres mod internettet.
- Templates mountes read-only og versioneres i Git.
- Backup omfatter templates/config/secrets, ikke sessions eller genererede dokumenter.
- HIF-01, HIF-02 og HIF-07 er compatibility-set.
- Alle 21 templates skal være konverteret og grønne før MVP-release.
- Templates og releases skal bestå statisk validering, binding-checks, minimal/normal/edge-profiler, DOCX/PDF-gates, security/privacy-tests, genericity-gate, nødvendig manuel visuel acceptance og Docker smoke-test.
- Dokumenttypespecifik backend-/renderingkode er ikke tilladt.

### Bevidste fravalg

MVP'en omfatter ikke:

- permanent dokumentbibliotek,
- dokumenthistorik eller revisionsmodel for brugeroprettede dokumenter,
- brugerkonti/login,
- database,
- SPA,
- microservices/Kubernetes,
- native mobilapp,
- AI-genereret dokumentindhold,
- integrationer til andre foreningssystemer,
- workflow/godkendelsesflow,
- import af historiske udfyldte Word-dokumenter.

### Handoff-artefakt

Den kanoniske samlede implementationsspecifikation er pakket som:

`docs/01_IMPLEMENTATIONSSPECIFIKATION.md`

Den er den primære kontrakt for implementationen. De øvrige dokumenter i slutpakken er støttedokumenter og referenceartefakter.

