---
title: "Definer validering og kompatibilitetsgates"
state: closed
label: "wayfinder:grilling"
mode: "HITL"
parent: "Find vejen til Hashøj IF dokumentbyggeren"
claimed_by: "project team"
blocked_by:
  - "Beslut template-schema og feltprimitiver"
  - "Beslut dokumentrenderingens kontrakt"
  - "Planlæg konvertering af de 21 Hashøj IF-skabeloner"
---

# Definer validering og kompatibilitetsgates

## Question

Hvilke automatiske checks og manuelle acceptance checks skal bevise, at en template-definition er gyldig, at et genereret dokument er korrekt, og at ændringer i motoren ikke bryder eksisterende templates?

## Resolution

### Beslutning

MVP'en bruger en kombination af automatiske valideringsgates og målrettede manuelle acceptance checks.

En template må kun aktiveres, og en release må kun godkendes, når de relevante gates er grønne.

### Statisk template-validering

Ved startup og i CI valideres hver TemplatePackage uden at starte wizard'en.

Validatoren kontrollerer mindst:

- gyldig YAML,
- krævede metadata,
- unik template-id/version,
- unikke step-id'er,
- unikke field-id'er inden for gældende scope,
- kun understøttede field types,
- gyldige validation-regler,
- gyldige defaults,
- `show_when` refererer til eksisterende felter,
- options findes og er gyldige for relevante felttyper,
- repeaters har gyldige child-fields,
- privacy/info/acknowledgement/consent metadata følger den låste kontrakt,
- `enabled: true` accepteres kun for en samlet gyldig TemplatePackage.

En ugyldig template må ikke vises som brugbar template på forsiden.

### DOCX-binding validation

`document.docx` valideres før en template kan aktiveres.

Validatoren skal mindst kontrollere:

- alle refererede datafelter eksisterer i template-/datakontrakten,
- kun tilladte docxtpl-constructs anvendes,
- Jinja/docxtpl-syntaks er gyldig,
- structural tags følger authoring-reglerne,
- ukendte placeholders/felt-ID'er giver hard failure.

Et YAML-felt behøver ikke nødvendigvis optræde i DOCX.

Eksempelvis kan:

- privacy-information,
- acknowledgement,
- consent-control,
- rent wizard-tekniske felter

være relevante for brugerrejsen uden at blive udskrevet i slutdokumentet.

### Automatiske testprofiler

Alle templates får mindst tre testdataprofiler.

#### `minimal`

Indeholder kun nødvendige/required data.

Formål:

- bevise at required-kontrakten er tilstrækkelig,
- bevise at optional data kan mangle,
- bevise at dokumentet stadig kan genereres.

#### `normal`

Indeholder realistiske Hashøj IF-data.

Formål:

- repræsentere normal brugeradfærd,
- verificere forventet preview og dokumentstruktur.

#### `edge`

Indeholder relevante edge cases, herunder:

- lange tekstværdier,
- tomme optional-felter,
- flere repeater-rækker,
- danske tegn,
- XML-specialtegn som `<`, `>` og `&`,
- Jinja-lignende tekst som `{{ example }}`,
- relevante min/max-grænser.

Alle tre profiler skal kunne gennemføre:

- schema/data validation,
- HTML-preview,
- DOCX-generation.

### PDF compatibility gate

En korrekt genereret DOCX skal kunne konverteres til PDF via LibreOffice.

Teknisk konverteringssucces er nødvendig, men ikke alene tilstrækkelig til at bevise layout-fidelitet.

Derfor kræves manuel PDF-layoutkontrol:

- ved første konvertering af hver template,
- ved template-ændringer der påvirker layout,
- ved ændringer i renderingmotor/LibreOffice/runtime, som realistisk kan påvirke output.

### Manuel visuel acceptance

Der kræves ikke pixel-identiske golden screenshots.

Ved første godkendelse af en template kontrolleres mindst:

- overskrifter og dokumenthierarki,
- tabeller,
- repeaters,
- wrapping af lange værdier,
- headers og footers,
- sideskift,
- portrait/landscape sections,
- checkbokse og symboler,
- danske tegn,
- tomme optional-sektioner,
- normal læsbarhed i DOCX,
- PDF-output.

Compatibility-settet får den dybeste manuelle gennemgang:

- HIF-01 Rollebeskrivelse,
- HIF-02 Opgavekort,
- HIF-07 Arrangementsskabelon.

### Generisk motor som release-gate

Dokumenttypespecifik backend-/renderingkode er ikke tilladt.

Eksempel på ikke-acceptabel løsning:

```python
if template_id == "hif-07":
    ...
```

Hvis en template kræver ny funktionalitet:

1. dokumentet forsøges modelleret med eksisterende primitives,
2. et konkret gap dokumenteres,
3. funktionaliteten implementeres generisk,
4. den konkrete template testes,
5. compatibility-settet regressionskøres.

En ændring, der kun løser én dokumenttype via specialkode, må ikke godkendes.

### Security/privacy negative tests

Testpakken skal indeholde negative tests, som mindst beviser:

- Jinja-lignende brugerinput evalueres ikke som template-kode,
- XML-specialtegn escapes korrekt,
- invalid required data kan ikke generere dokument,
- manglende required data kan ikke generere dokument,
- request/form payloads skrives ikke til application logs,
- generated document content logges ikke,
- temp-artifacts slettes efter flow/cleanup,
- session-data lagres ikke i `localStorage`,
- session-data lagres ikke i `sessionStorage`,
- HTMX history cache bruges ikke til wizard-data,
- templates med markerede højrisiko/privacy-forhold kan ikke aktiveres uden krævet governance-information.

### Regression gate

Enhver ændring i:

- core,
- schema,
- validation,
- rendering,
- template-loading,
- DOCX pipeline,
- PDF pipeline

skal regressionskøre alle installerede templates.

Release må kun godkendes når:

- alle 21 templates validerer,
- testprofilerne gennemfører relevante flows,
- HTML-preview genereres,
- DOCX genereres,
- PDF-konvertering fungerer,
- compatibility-settet består alle compatibility-gates,
- nødvendige manuelle visual checks er godkendt,
- Docker Compose smoke-test starter systemet,
- `/health` er grøn,
- ingen dokumenttypespecifik backend-/renderingkode er introduceret.

### Gate for nye templates efter MVP

En ny template kan tilføjes uden ændring af Python-kode, hvis den kan beskrives med de eksisterende generiske primitives.

Før `enabled: true` må den dog bestå de samme relevante gates:

- statisk schema-validering,
- binding validation,
- testprofiler,
- DOCX,
- PDF,
- security/privacy checks,
- manuel visuel acceptance ved første introduktion.

### CI versus manuel acceptance

Automatiske gates skal kunne køres i CI/lokalt som én samlet validerings-/testkommando.

Manuel visuel acceptance registreres som en eksplicit godkendelse, når den er påkrævet.

CI må ikke forsøge at erstatte menneskelig layoutvurdering med et falsk pixel-perfekt signal.

### Deployment smoke test

Release-validation skal kunne køres i en produktionslignende Docker Compose-konfiguration.

Smoke-testen skal mindst bevise:

- Caddy/app stack kan starte,
- app-container er healthy,
- `/health` svarer korrekt,
- read-only template-directory kan læses,
- mindst en repræsentativ DOCX-generation fungerer i containeren,
- PDF-generation via LibreOffice fungerer i containeren,
- temp cleanup kan gennemføres.

### Bevidste fravalg

MVP'en kræver ikke:

- pixel-perfect screenshot regression for alle dokumenter,
- permanent lagring af test-genererede dokumenter i produktion,
- dokumenttypespecifik acceptance-kode,
- automatiseret semantisk AI-vurdering af dokumentoutput,
- production observability-platform som del af compatibility-gaten.

### Konsekvenser for handoff

**Lås implementationens handoff-specifikation** skal indeholde:

- statisk template-validator,
- binding-validator,
- `minimal/normal/edge` testprofiler,
- DOCX- og PDF-gates,
- security/privacy negative tests,
- genericity-gate,
- manual visual acceptance,
- full-template regression,
- Docker Compose smoke-test,
- definitionen af hvornår en template må være `enabled: true`.

