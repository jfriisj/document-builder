# Hashøj IF Dokumentbygger — Kanonisk implementationsspecifikation

**Status:** Godkendt til implementation  
**Wayfinder:** Afsluttet  
**Mål:** MVP for alle 21 Hashøj IF-dokumenttyper

## 1. Produktmål

Løsningen er en enkel, guided, Docker-hostet dokumentgenerator for Hashøj IF.

En bruger skal kunne:

1. åbne siden,
2. vælge en dokumenttype,
3. udfylde ét guidet trin ad gangen,
4. gå frem og tilbage uden datatab i den aktive session,
5. kontrollere oplysningerne,
6. se et HTML-preview,
7. rette oplysninger,
8. downloade dokumentet som DOCX eller PDF.

MVP'en er en generator, ikke et dokumentbibliotek.

## 2. MVP-scope

MVP-release omfatter alle 21 eksisterende Hashøj IF-dokumenttyper.

Compatibility-settet er:

- HIF-01 Rollebeskrivelse
- HIF-02 Opgavekort
- HIF-07 Arrangementsskabelon

De tre templates bruges til at bevise motorens generalitet. MVP'en er først færdig, når alle 21 fungerer via samme generiske mekanisme.

## 3. Ude af scope

MVP'en indeholder ikke:

- permanent dokumentbibliotek,
- dokumenthistorik eller dokumentrevisioner,
- brugerkonti eller login,
- database,
- dashboards,
- workflow/godkendelsesflow,
- eksterne integrationer,
- AI-genereret dokumenttekst,
- SPA,
- Kubernetes/microservices,
- native mobilapp,
- import af historiske udfyldte Word-dokumenter.

## 4. Teknologistack

### Core/backend

- Python 3
- PyYAML
- Pydantic som valideringsværktøj
- docxtpl
- python-docx som supplement
- LibreOffice headless til PDF-konvertering

### Webadapter

- FastAPI
- Jinja2
- HTMX
- almindelig CSS
- minimal vanilla JavaScript

### Arkitekturregel

Core/application-laget må ikke afhænge af FastAPI, HTMX eller webspecifik teknologi.

FastAPI er en adapter omkring den generiske core.

## 5. Domænemodel

MVP'en har kun tre centrale runtime-begreber:

```text
TemplatePackage
      │
      ▼
GenerationSession
      │
      ▼
GeneratedArtifact
```

### TemplatePackage

Indeholder:

- stabil `id`,
- `version`,
- `enabled`,
- metadata,
- `template.yaml`,
- `document.docx`,
- eventuelle assets.

### GenerationSession

Transient runtime-state:

- opaque/random session-id,
- template-id,
- template-version,
- current step,
- values,
- created_at,
- expires_at / last activity.

Der findes ingen `User`, `Document`, `DocumentRevision`, `DocumentStatus` eller permanent ejerrelation.

### GeneratedArtifact

Kortlivet output:

- filename,
- format,
- MIME type,
- temp-reference/path.

Artifact returneres til brugeren og slettes bagefter.

## 6. Template-struktur

Én dokumenttype svarer til én mappe:

```text
templates/
  hif-01-role/
    template.yaml
    document.docx
    assets/
```

Templates opdages automatisk fra den konfigurerede template-directory.

Regler:

- gyldig + `enabled: true` → synlig,
- `enabled: false` → skjult,
- ugyldig → må ikke eksponeres.

Templates vedligeholdes af en teknisk administrator via filer/Git. Der bygges ingen grafisk template-editor i MVP'en.

## 7. YAML-kontrakt

YAML er source of truth for formularen.

Minimum:

```yaml
id: hif-01-role
version: 1
enabled: true
title: Rollebeskrivelse
category: Organisation
description: Beskriv ansvar, opgaver og forventninger til en rolle.

steps:
  - id: basic
    title: Grundoplysninger
    fields:
      - id: role_name
        type: text
        label: Hvad hedder rollen?
        required: true
```

### Feltprimitiver

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

E-mail, telefon og URL modelleres som `text` + `format`.

### Valideringsregler

- `required`
- `min_length`
- `max_length`
- `min`
- `max`
- `min_items`
- `max_items`
- `format`
- `pattern`

### Conditions

Tilladte simple operators:

- `equals`
- `not_equals`
- `in`
- `not_in`

Ingen Python-, JavaScript- eller vilkårlige expressions i YAML.

### Defaults

Kun statiske defaults.

Ingen formulas, beregnede værdier eller inter-field expressions i MVP'en.

### Repeaters

Lister/tabeller modelleres som `repeater` med child-fields.

Dataformatet er en liste af objekter.

## 8. Stable field IDs

Field `id` er den stabile kontrakt mellem:

- YAML,
- GenerationSession.values,
- HTML-preview,
- DOCX-rendering.

Labels, help og placeholders må ændres uden at ændre data-kontrakten.

Breaking ændring af field-ID kræver ny template-version.

## 9. UX-kontrakt

Brugerrejsen er:

```text
Forside
  ↓
Dokumentintro
  ↓
Wizard: ét trin ad gangen
  ↓
Kontrol
  ↓
HTML-preview
  ↓
Ret oplysninger
  ↓
Generér
  ↓
DOCX / PDF
```

Wizard understøtter:

- progress-indikator,
- tydelig step-title,
- required-markering,
- placeholder,
- help,
- example,
- repeaters,
- contextual privacy-info,
- eksplicit Tilbage/Næste.

Browserens Back-funktion må ikke være nødvendig for wizard-state.

## 10. Session og persistence

MVP'en bruger ingen SQLite eller anden database.

GenerationSession ligger kun i RAM.

### Session lifetime

- 60 minutters inactivity-TTL.
- Gyldig aktivitet forlænger TTL.
- Efter timeout slettes sessionen.
- Restart/deploy/servercrash mister aktive kladder.

### Browser

Browseren indeholder kun opaque session-id.

Session-cookie:

- HttpOnly
- Secure under HTTPS
- SameSite=Lax eller strengere

Ingen formularpayload i:

- localStorage,
- sessionStorage,
- HTMX history cache.

## 11. Dokumentrendering

DOCX er det autoritative dokumentlayout og primære outputformat.

Flow:

```text
GenerationSession.values
        │
        ▼
document.docx + docxtpl
        │
        ▼
rendered.docx
        │
        ├── download DOCX
        │
        ▼
LibreOffice headless
        │
        ▼
rendered.pdf
```

### Tilladte docxtpl-mønstre

- simple variables
- simple if/conditions
- loops
- docxtpl structural paragraph/row/cell/run tags hvor nødvendigt

Ingen custom Python functions eller dokumenttypespecifik backendkode i templates.

### Layoutansvar

`document.docx` ejer:

- Word styles,
- margins,
- headers/footers,
- sideskift,
- section breaks,
- portrait/landscape,
- tabeller,
- visuel struktur.

YAML/core må ikke indeholde dokumenttypespecifikke layoutregler.

### Tomme værdier

- optional scalar → tom værdi,
- tom repeater → ingen iteration,
- required data mangler → generation blokeres.

Sektioner skjules via eksplicit condition i dokumenttemplate, ikke via gæt i motoren.

## 12. Rendering-fejl

- ukendt DOCX field-ID → ugyldig template,
- ugyldig docxtpl/Jinja-syntaks → ugyldig template,
- manglende required data → ingen generation,
- DOCX-rendering failure → ingen delvis fil,
- PDF failure → DOCX forbliver gyldig/downloadbar.

Brugeren får generisk fejlbesked. Logs må ikke indeholde formularpayload eller dokumentindhold.

## 13. Escaping og sikker inputbinding

Brugerinput er altid data, aldrig template-kode.

Krav:

- XML-specialtegn escapes sikkert,
- `{{ ... }}` fra bruger behandles som tekst,
- brugerinput evalueres aldrig som Jinja,
- server-side validation er autoritativ.

## 14. Temp-filer

Temp-data er transient.

- dedikeret, ikke-offentlig temp-directory,
- slettes efter levering når teknisk muligt,
- stale artifacts ryddes senest efter 10 minutter,
- temp-data inkluderes ikke i backup.

## 15. Privacy/GDPR-baseline

Ingen permanent lagring betyder ikke, at behandlingen er GDPR-fri.

Krav:

- dataminimering pr. template,
- formål og relevant behandlingsgrundlag dokumenteres pr. relevant template,
- privacy notice er separat fra acknowledgement/consent,
- consent bruges kun, når det reelt er behandlingsgrundlaget,
- templates med særlige/højrisikodata kræver særskilt privacy/legal gate,
- request bodies og dokumentindhold må ikke logges,
- ingen tracking/analytics/marketing i MVP,
- kun teknisk nødvendig sessionteknologi,
- HTTPS er obligatorisk,
- ekstern hosting kræver vurdering af databehandlerforhold.

## 16. Deployment

Produktion er én Docker Compose-stack med to services:

```text
Internet
   │
  HTTPS
   ▼
 Caddy
   │
 intern Docker network
   ▼
 FastAPI app
```

### Regler

- kun Caddy publiceres mod internettet,
- FastAPI publiceres ikke direkte på hosten,
- Caddy håndterer TLS og HTTP→HTTPS,
- templates mountes read-only,
- LibreOffice ligger i app-containeren,
- app har `/health`,
- Compose har healthcheck og restart policy.

## 17. Backup og restore

Permanent state:

- templates,
- compose-konfiguration,
- Caddyfile,
- ikke-hemmelig deployment-config,
- secrets/.env opbevaret sikkert separat,
- Git-historik.

Ikke backup:

- RAM sessions,
- generated DOCX/PDF,
- temp-filer.

Restore:

```text
ny Docker-host
  ↓
installer Docker
  ↓
clone repository/config
  ↓
gendan secrets
  ↓
docker compose pull
  ↓
docker compose up -d
  ↓
healthcheck
```

## 18. Image-versionering og rollback

Produktion bruger versionsmærkede images.

Ikke kun `latest`.

Update:

```text
vælg ny version
  ↓
docker compose pull
  ↓
docker compose up -d
  ↓
healthcheck
```

Rollback = tilbage til seneste kendte fungerende image-tag + Compose restart.

## 19. Konverteringsplan for de 21 templates

### Bølge A — compatibility proof

- HIF-01 Rollebeskrivelse
- HIF-02 Opgavekort
- HIF-07 Arrangementsskabelon

### Bølge B — simple/sektion-baserede

- HIF-03 Overdragelsesdokument
- HIF-08 Projektbeskrivelse
- HIF-09 Mødereferat
- HIF-12 Frivillig og vagtinstruks
- HIF-13 Introduktion nye frivillige
- HIF-17 Hændelses- og skadesrapport
- HIF-20 Kommunikationsskabelon

### Bølge C — register/repeater/tabel/privacy-tunge

- HIF-04 Årshjul
- HIF-05 Kontaktregister
- HIF-06 Leverandør- og aftaleregister
- HIF-10 Beslutningslog
- HIF-11 Handlingsliste
- HIF-14 Nøgle- og adgangsregister
- HIF-15 Udstyrs- og inventarliste
- HIF-16 Vedligeholdelsesplan
- HIF-18 Indkøbs- og bestillingsskabelon
- HIF-19 Sponsorprofil og aftalecheckliste
- HIF-21 GDPR- og samtykkeoversigt

### Regel for gaps

Ingen specialkode.

Hvis en faktisk template ikke kan udtrykkes:

1. forsøg eksisterende primitives,
2. dokumentér konkret gap,
3. vurder generisk løsning,
4. udvid motor/schema generisk,
5. regressionskør compatibility-settet.

Ingen primitives til hypotetiske fremtidige behov.

## 20. Definition of Converted

En template er først konverteret, når:

- auto-discovery virker,
- YAML er valid,
- wizard fungerer,
- frem/tilbage bevarer data,
- repeaters/conditions virker,
- HTML-preview er semantisk korrekt,
- DOCX genereres,
- PDF genereres acceptabelt,
- tomme/lange værdier testes,
- danske tegn testes,
- privacy vurderes hvor relevant,
- ingen dokumenttypespecifik Python-kode er tilføjet.

## 21. Validerings- og release-gates

### Static template validation

Kontroller mindst:

- YAML syntax,
- metadata,
- id/version,
- step-/field-ID uniqueness,
- field types,
- validation rules,
- defaults,
- show_when references,
- options,
- repeaters,
- privacy metadata,
- enabled state.

### DOCX binding validation

Kontroller:

- referenced fields findes,
- allowed docxtpl constructs,
- valid syntax,
- structural-tag rules.

### Testprofiler pr. template

- `minimal`
- `normal`
- `edge`

Edge dækker bl.a.:

- lange værdier,
- tomme optional-felter,
- repeaters,
- danske tegn,
- `<`, `>`, `&`,
- `{{ ... }}` som brugerinput.

### Security/privacy negative tests

Bevis mindst:

- template-kode kan ikke injiceres via brugerinput,
- escaping virker,
- invalid required data blokeres,
- payloads logges ikke,
- temp cleanup virker,
- browser storage ikke bruges til wizard-data,
- privacy-gates respekteres.

### Manual visual acceptance

Kontroller hvor relevant:

- struktur,
- tabeller,
- wrapping,
- headers/footers,
- sideskift,
- portrait/landscape,
- checkbokse/symboler,
- danske tegn,
- optional-sektioner,
- DOCX,
- PDF.

HIF-01/02/07 får den dybeste compatibility-gennemgang.

### Release gate

Release er kun grøn, når:

- alle 21 templates validerer,
- relevante testprofiler består,
- HTML/DOCX/PDF pipeline fungerer,
- compatibility-set består,
- krævede manuelle visual checks er godkendt,
- Docker Compose smoke-test består,
- `/health` er grøn,
- ingen dokumenttypespecifik backend-/renderingkode findes.

## 22. Implementationsrækkefølge

En praktisk rækkefølge er:

1. repository/package skeleton og core boundaries,
2. TemplatePackage discovery + YAML validation,
3. GenerationSession + RAM session store,
4. generisk Jinja2/HTMX wizard,
5. HTML-preview,
6. docxtpl DOCX renderer,
7. LibreOffice PDF pipeline + temp cleanup,
8. compatibility-set HIF-01/02/07,
9. automatiske gates/testprofiler,
10. resterende 18 templates efter bølgeplan,
11. Caddy/Compose deployment,
12. fuld 21-template regression og MVP acceptance.

Rækkefølgen er en implementationstilrettelæggelse; kontrakterne ovenfor er de bindende krav.

## 23. MVP acceptance

MVP'en er færdig, når:

- en ikke-teknisk frivillig kan forstå flowet,
- alle 21 templates kan vælges,
- guided help/progress/back/next fungerer,
- HTML-preview og rettelse fungerer,
- DOCX og PDF kan genereres,
- compatibility-settet beviser generisk motor,
- alle øvrige templates bruger samme mekanisme,
- nye templates kan tilføjes uden backendkode, hvis primitives rækker,
- Docker Compose deployment fungerer,
- alle validerings-/security-/compatibility-gates er grønne.

Denne fil er den kanoniske implementationskontrakt.
