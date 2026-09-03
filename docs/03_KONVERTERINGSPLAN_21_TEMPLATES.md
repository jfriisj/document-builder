---
title: "Planlæg konvertering af de 21 Hashøj IF-skabeloner"
state: closed
label: "wayfinder:grilling"
mode: "HITL"
parent: "Find vejen til Hashøj IF dokumentbyggeren"
claimed_by: "project team"
blocked_by:
  - "Beslut template-schema og feltprimitiver"
  - "Beslut dokumentrenderingens kontrakt"
---

# Planlæg konvertering af de 21 Hashøj IF-skabeloner

## Question

Hvordan skal de 21 eksisterende skabeloner klassificeres og konverteres til template-definition + DOCX-layout, hvilke få repræsentative templates skal bruges som compatibility set, og hvilke variationer skal systemet bevise før resten konverteres?

## Resolution

### Beslutning

Konverteringen af Hashøj IF's 21 eksisterende Word-skabeloner planlægges som en kontrolleret migration til én `TemplatePackage` pr. dokumenttype.

Målet er at bevise, at alle dokumenttyper kan håndteres af den generiske YAML-/DOCX-motor uden dokumenttypespecifik Python-kode.

### Hvad konverteres

MVP'en konverterer de **blanke dokumenttemplates**.

Eksisterende allerede udfyldte Word-dokumenter importeres ikke til wizard'en som del af denne migration.

De eksisterende Word-skabeloner bruges som reference for:

- dokumentets indhold,
- visuelle struktur,
- felter,
- tabeller,
- sektioner,
- metadata,
- dokumentets formål.

### Én TemplatePackage pr. dokumenttype

Hver dokumenttype får sin egen mappe:

```text
templates/
  hif-01-role/
    template.yaml
    document.docx
    assets/
```

`template.yaml` beskriver:

- metadata,
- wizard-trin,
- felter,
- labels,
- hjælp,
- validering,
- repeaters,
- conditions,
- privacy-information.

`document.docx` beskriver det endelige Word-layout og docxtpl-bindingerne.

Der oprettes ikke Python-kode pr. dokumenttype.

### Compatibility-set

Det allerede valgte compatibility-set fastholdes:

1. **HIF-01 Rollebeskrivelse**
   - simple felter,
   - sektioner,
   - almindelig data-binding.

2. **HIF-02 Opgavekort**
   - repeaters,
   - tabeller,
   - checkbokse,
   - gentagne strukturer.

3. **HIF-07 Arrangementsskabelon**
   - større dokumentstruktur,
   - flere trin,
   - kombination af forskellige felt- og layouttyper.

Disse tre konverteres først.

Hvis compatibility-settet afslører et reelt gap i schema eller renderingmotor, stoppes massekonverteringen, indtil gap'et er vurderet og løst generisk.

### Konverteringsbølger

#### Bølge A — compatibility proof

- HIF-01 Rollebeskrivelse
- HIF-02 Opgavekort
- HIF-07 Arrangementsskabelon

#### Bølge B — primært simple/sektion-baserede templates

- HIF-03 Overdragelsesdokument
- HIF-08 Projektbeskrivelse
- HIF-09 Mødereferat
- HIF-12 Frivillig og vagtinstruks
- HIF-13 Introduktion nye frivillige
- HIF-17 Hændelses- og skadesrapport
- HIF-20 Kommunikationsskabelon

#### Bølge C — register/repeater/tabel/privacy-tunge templates

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

Klassificeringen er kun arbejds-/konverteringsrækkefølge og ændrer ikke dokumenternes funktion.

### Visuel fidelitet

Konverteringen skal bevare dokumenternes visuelle identitet og informationsstruktur.

Følgende skal bevares, hvor relevant:

- Hashøj IF-identitet,
- overskrifter,
- tabeller,
- dokumenthierarki,
- metadata,
- læsbar struktur,
- centrale visuelle skel.

Tekniske Word-konstruktioner behøver ikke bevares 1:1, hvis de er skrøbelige eller unødigt komplekse i docxtpl.

En teknisk forenkling er tilladt, når:

- informationen bevares,
- dokumentets formål bevares,
- resultatet fortsat er visuelt og funktionelt acceptabelt.

### Fast konverteringsproces

Hver template følger samme proces:

```text
eksisterende DOCX
     ↓
identificér input/data
     ↓
map til eksisterende feltprimitiver
     ↓
design wizard-trin i YAML
     ↓
tilføj stabile field IDs
     ↓
indsæt docxtpl-bindinger i document.docx
     ↓
test HTML preview
     ↓
generér DOCX
     ↓
generér PDF
     ↓
acceptance
```

Der må ikke springes direkte til specialkode, hvis en eksisterende template ikke umiddelbart passer.

### Gaps i schema eller motor

Hvis en af de 21 templates kræver noget, som det låste schema eller renderingkontrakten ikke kan udtrykke:

1. dokumentet forsøges først modelleret med eksisterende primitives,
2. hvis det ikke er realistisk, registreres et konkret schema-/motor-gap,
3. gap'et vurderes mod flere templates,
4. en generisk udvidelse kan derefter besluttes,
5. dokumenttypespecifik Python-kode er ikke en acceptabel genvej.

### Ingen hypotetiske primitives

Schema og renderingmotor udvides ikke for tænkte fremtidige behov.

Nye primitives eller renderingfunktioner tilføjes kun, hvis mindst én af de faktiske 21 Hashøj IF-templates demonstrerer et konkret behov.

Dette fastholder den eksisterende beslutning om et lille deklarativt schema frem for et generelt programmeringssprog.

### Definition of converted

En template regnes først som konverteret, når:

- den opdages automatisk,
- YAML-definitionen er gyldig,
- alle relevante wizard-trin kan udfyldes,
- frem/tilbage bevarer data,
- repeaters/conditions fungerer, hvor de anvendes,
- HTML-preview er semantisk korrekt,
- DOCX genereres korrekt,
- PDF genereres med acceptabel fidelitet,
- tomme værdier er testet,
- lange værdier er testet,
- danske tegn fungerer,
- dokumenttypespecifik Python-kode ikke er tilføjet,
- privacy-information er vurderet, hvor relevant.

De præcise automatiske og manuelle checks fastlægges i **Definer validering og kompatibilitetsgates**.

### MVP-krav

Compatibility-settet bruges til at bevise motorens generalitet.

MVP'en er dog først komplet, når **alle 21 dokumenttyper** er konverteret og tilgængelige gennem samme generiske mekanisme.

### Bevidste fravalg

Konverteringsplanen omfatter ikke:

- import af historiske udfyldte Word-dokumenter,
- dokumenttypespecifik Python-backend,
- separate renderers pr. dokumenttype,
- nye primitives baseret på hypotetiske behov,
- krav om pixel-identisk reproduktion af alle gamle Word-detaljer.

### Konsekvenser for senere tickets

- **Definer validering og kompatibilitetsgates** skal nu låse de automatiske checks, manuelle acceptance checks og regressionskrav, som gælder for compatibility-settet og alle 21 templates.
- **Lås implementationens handoff-specifikation** skal inkludere de tre konverteringsbølger, Definition of Converted og reglen om generiske gaps frem for specialkode.

