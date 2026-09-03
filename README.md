# Document Builder

Enkel, guided, Docker-hostet dokumentgenerator til deklarativ oprettelse af standardiserede dokumenter (DOCX og PDF) uden permanent datalagring.

Document Builder er en generisk motor, der driver trinvise formularer, kontrol, semantisk HTML-preview og generering af Word- og PDF-filer baseret på deklarative skabelonpakker (`template.yaml` + `document.docx`).

Repositoryet indeholder desuden som referenceimplementation:
- **Hashøj IF Reference Template Pack**: Samtlige 21 foreningsdokumenter (HIF-01 til HIF-21), som demonstrerer en komplet, funktionel anvendelse af den generiske motor til en virkelig organisation.

### Generisk motor og skabelonudskiftning
- **Generisk motor**: Applikationskernen indeholder ingen skabelonspecifik Python-kode, ingen branches på skabelon-ID'er og ingen organisation-specifik branding i den generiske brugergrænseflade.
- **Udskiftelig skabelonmappe**: Enhver anden gyldig skabelonmappe med deklarative `template.yaml`- og `document.docx`-filer kan monteres i motoren uden kildekodeændringer.
- **Referencepakke-validering**: De medfølgende kompatibilitetstests for HIF-01 til HIF-21 validerer systematisk den bundtede referenceimplementation mod motorens generiske layout- og konverteringskrav.

## Status

Projektet implementeres i henhold til den autoritative specifikation ([`docs/01_IMPLEMENTATIONSSPECIFIKATION.md`](docs/01_IMPLEMENTATIONSSPECIFIKATION.md)).

- **Milestone 6 gennemført**: Alle 21 kanoniske `TemplatePackages` i Hashøj IF-referencepakken er implementeret. 20 skabeloner er offentligt aktive (`enabled: true`), mens HIF-17 Hændelses- og skadesrapport (`hif-17-incident`) forbliver deaktiveret (`enabled: false`) under den eksplicitte privatlivs- og juridiske aktiveringsport (indeholder potentielle helbreds- og skadesoplysninger).
- **Milestone 7**: Docker Compose produktionsdeployment, Caddy reverse proxy (automatisk HTTPS/TLS), headless LibreOffice integreret i app-image med deterministisk skrifttypesubstitution for Aptos/Aptos Display (Carlito sans-serif), read-only skabelon-mount, netværksisolation (FastAPI port 8000 upubliceret) samt automatiserede release-gates implementeret og godkendt. HIF-17 forbliver bevidst deaktiveret, indtil den separate privacy/legal activation gate er afklaret.

Alle 21 skabeloner vedligeholdes 100% deklarativt via `template.yaml` og `document.docx` uden dokumentspecifik Python-kode i applikationskernen.

## MVP-mål

At levere en generisk motor, der guider brugeren igennem trinvis udfyldelse, kontrol, HTML-preview og generering af DOCX og PDF via en webbrowser uden krav om login eller database, med Hashøj IF-pakken som fuldt ud funktionel referenceimplementation.

## Generisk brugerrejse

Brugerrejsen er udelukkende drevet af skabelonpakker og formularkontrakter i YAML:

```text
Forside
   ↓
Dokumentintro
   ↓
GenerationSession oprettes i RAM
   ↓
Wizard: ét trin ad gangen
   ↓
Autoritativ server-validering & bevarelse af data frem/tilbage
   ↓
Kontrolside med direkte redigeringslinks
   ↓
Semantisk HTML-preview
   ↓
Generér og download DOCX / PDF
   ↓
Ret oplysninger / ny generering (sessionen bevares)
```

## Session og datasikkerhed (RAM-only)

- **Ingen database**: `GenerationSession` eksisterer udelukkende i serverens arbejdshukommelse (RAM).
- **60 minutters inaktivitets-TTL**: Sessioner udløber automatisk efter 60 minutters inaktivitet. Gyldig aktivitet forlænger timeout.
- **Opaque session-cookie**: Browseren modtager kun et uigennemskueligt, kryptografisk tilfældigt session-ID (`document_builder_session_id`, `HttpOnly`, `SameSite=Lax`, `Secure` under HTTPS). Formularværdier og personoplysninger gemmes aldrig i cookies.
- **Ingen browser-persistence**: Formulardata lagres ikke i `localStorage`, `sessionStorage` eller HTMX history cache (`hx-history="false"`).
- **Privatlivs- og logningsdisciplin**: Formularbodies, sessionsværdier og dokumentindhold logges aldrig.
- **HIF-17 aktiveringsport**: HIF-17 forbliver skjult fra offentlig discovery, indtil der foreligger en eksplicit godkendelse.

## DOCX- og PDF-generering

- **DOCX-rendering (`docxtpl`)**:
  - `document.docx` er det autoritative layoutdokument.
  - Brugerinput indsættes som rene data med automatisk XML-escaping (`<`, `>`, `&`).
  - Brugerindtastninger fortolkes aldrig som Jinja-kode.
  - Inaktive felter (under `show_when`) filtreres automatisk fra rendering-konteksten, så forældede værdier ikke lækker til dokumentet.
- **DOCX-binding validering**:
  - `document.docx` valideres statisk ved indlæsning med leksikalsk scope og streng AST-grammatik.
  - Ukendte feltreferencer, `info`-felter (der ikke udgør dokumentdata), `super`, `loop` uden for løkker eller ikke-tilladte Jinja-konstruktioner afviser skabelonen ved indlæsning.
- **PDF-konvertering (LibreOffice headless)**:
  - PDF afledes altid direkte fra den succesfuldt genererede DOCX-fil via LibreOffice (`soffice --headless --convert-to pdf`).
  - LibreOffice er pakket direkte i applikations-imaget (`libreoffice-writer-nogui`). Der benyttes ingen separat PDF-mikrotjeneste.
  - **Procesisoleret profil**: Hver konvertering tildeles en isoleret, midlertidig LibreOffice-brugerprofil (`-env:UserInstallation=file://...`), hvilket sikrer stabil parallel eksekvering uden profilkonflikter under runtime-brugeren `app` (uid 10001).
  - **Fejlhåndtering**: Hvis PDF-konvertering fejler eller ikke er tilgængelig, bevares `GenerationSession`, fejlforsøgets temp-filer ryddes op straks, og brugeren tilbydes direkte at hente DOCX.

## Transient håndtering af artefakter

- Genererede DOCX- og PDF-filer skrives til en dedikeret, ikke-offentlig midlertidig mappe (`/tmp/document_builder_artifacts`).
- Fil- og mappenavne dannes med uigennemskuelige tilfældige tokens uden bruger- eller formulardata.
- **Normal livscyklus**: Efter streaming via `FileResponse` slettes den dedikerede midlertidige mappe automatisk af en baggrundsopgave (`BackgroundTasks`).
- **10-minutters sikkerhedsnet**: Filer og mapper ældre end 10 minutter ryddes automatisk og opportunistisk som sikkerhedsnet ved procesnedbrud eller afbrudte forbindelser.
- Der oprettes ingen permanente download-historikker, sessionstabeller eller fillister.

## Skabeloner og auto-discovery

Dokumenttyper organiseres som filbaserede `TemplatePackages`:

```text
templates/
  hif-01-role/
    template.yaml
    document.docx
    assets/  (valgfrit)
```

- Skabeloner bages **ikke** ind i applikations-imaget. I produktion modtages de som et read-only mount (`./templates:/app/templates:ro`) fra host/Git.
- **`template.yaml` er source of truth** for formularstruktur, trin, felter, validering, betinget visning (`show_when`), repeaters og privacy-metadata.
- **`discover_templates(root)`**: Scanner skabelonmapper, validerer schema og bindings, og returnerer 21 pakker.
- **`discover_enabled_templates(root)`**: Returnerer de 20 aktive skabeloner.

---

## Produktionsarkitektur og Deployment (Docker Compose)

### Arkitektur

```text
Internet
   |
 HTTPS (Port 443 / Port 80 redirect)
   v
 Caddy (Reverse Proxy, automatisk TLS)
   |
 Intern Docker-netværk
   v
 FastAPI App (uvicorn, port 8000, 1 worker, RAM-only GenerationSession, LibreOffice headless)
```

**Sikkerhedskontrakt:**
- Kun Caddy publicerer porte til hosten (`80` og `443`).
- FastAPI-containeren lytter internt på port `8000` og er **ikke** tilgængelig fra hostens netværk.
- Applikations-imaget kører som uprivilegeret bruger (`app`, uid 10001).
- Skabelonmappen `./templates` er monteret strengt **read-only** (`:ro`).

### Forudsætninger

- Docker Engine >= 20.10
- Docker Compose v2 (eller `docker compose` plugin)

### Konfiguration

1. Opret en `.env`-fil ud fra skabelonen:
   ```bash
   cp .env.example .env
   ```

2. Tilpas variabler i `.env`:
   - `DOMAIN`: Sæt til det ønskede offentlige domænenavn (f.eks. `docs.example.com`) for automatisk offentligt certifikat (Let's Encrypt / ZeroSSL). For lokal test anvendes `localhost` (Caddy benytter da sit indbyggede lokale CA).
   - `APP_IMAGE`: Skal altid være en eksplicit versioneret reference, f.eks. `document-builder:0.1.0` (aldrig en ukvalificeret `latest`).
   - `HTTP_PORT` og `HTTPS_PORT`: Standard er `80` og `443`.

### Opstart og drift

Byg og start stacken i baggrunden:

```bash
docker compose up -d --build
```

Tjek status på kørende containere og sundhed:

```bash
docker compose ps
```

Containeren `app` rapporterer sundhedstilstand (`healthy`) baseret på `/health`. Caddy afventer denne tilstand før opstart.

Se applikationslogs:

```bash
docker compose logs -f app
docker compose logs -f caddy
```

Sundhedstjek via Caddy (HTTPS):

```bash
curl -k https://localhost/health
# {"status":"ok"}
```

Genstart eller stop:

```bash
docker compose restart
docker compose down
```

### Opdatering og Rollback

1. **Opdatering**:
   - **Lokalt bygget image**:
     - Byg det nye image med opdateret versionstag:
       ```bash
       docker build -t document-builder:0.2.0 .
       ```
     - Opdater `APP_IMAGE=document-builder:0.2.0` i `.env`.
   - **Image fra eksternt registry**:
     - Opdater `APP_IMAGE=registry.example.com/document-builder:0.2.0` i `.env`.
     - Hent imaget: `docker compose pull app`
   - **Udrulning**:
     - Genstart servicen med den nye version (Docker Compose udfører container-erstatning med et kort genstartsinterval):
       ```bash
       docker compose up -d
       ```
2. **Rollback**:
   - **Lokalt bygget image**: Sæt `APP_IMAGE` i `.env` tilbage til forrige fungerende tag (f.eks. `document-builder:0.1.0`).
   - **Image fra eksternt registry**: Sæt `APP_IMAGE` i `.env` tilbage til forrige version.
   - Anvend rollback-versionen:
     ```bash
     docker compose up -d
     ```

### Backup og Restore

- **Backup-omfang**:
  - `templates/`: Kildekoden til alle skabeloner (vedligeholdes autoritativt i Git-repositoryet).
  - Caddy persistent volume (`caddy_data`): Indeholder udstedte TLS-certifikater og CA-nøgler, så ACME rate-limits ikke overskrides ved genstart.
  - `.env` og `compose.yaml`: Drifts- og miljøkonfiguration.
- **Hvad der BEVIDST IKKE genskabes eller sikkerhedskopieres**:
  - Ingen database (findes ikke).
  - Ingen brugersessioner (sessionsdata er 100% RAM-only og forsvinder ved container-genstart).
  - Ingen genererede dokumenter (filer i `/tmp/document_builder_artifacts` er midlertidige og slettes umiddelbart efter download).

#### Praktisk Restore-procedure
Ved genetablering eller flytning til en ny host:
1. **Klon kilderepository og skabeloner**:
   ```bash
   git clone <repo-url> /opt/document-builder
   cd /opt/document-builder
   ```
2. **Gendan driftskonfiguration (`.env`)**:
   Kopier sikkerhedskopieret `.env` eller opsæt ud fra `.env.example` med korrekt `DOMAIN` og `APP_IMAGE`.
3. **Gendan Caddy TLS-data (`caddy_data`)**:
   Gendan eventuel backup af Caddy-volumenet til Dockers volumen-sti (eller lad Caddy genudstede certifikater automatisk ved opstart).
4. **Start og verificer**:
   ```bash
   docker compose up -d
   python3 scripts/release_validation.py
   ```


### Automatiseret release- og container-validering

Kør den samlede verifikationspakke (tester Gates A gennem G inkl. Caddy HTTPS, netværksisolation, read-only skabelonmount, headless LibreOffice, og transient artefaktoprydning):

```bash
python3 scripts/release_validation.py
```

---

## Lokal udvikling og test

Projektet bruger `uv` til pakke- og udviklingsstyring:

```bash
# Synkronisér afhængigheder
uv sync

# Kør testsuite i lokalt miljø (LibreOffice-afhængige tests skippes automatisk hvis soffice mangler)
uv run pytest -v

# Kør fuld regression i det officielle container-miljø med LibreOffice (338 tests, 0 skips)
docker run --rm -v $(pwd):/workspace -w /workspace -e UV_PROJECT_ENVIRONMENT=/tmp/venv document-builder:0.1.0 uv run pytest -v

# Start lokal udviklingsserver med hot-reload
uv run uvicorn hashoej_document_builder.web.app:app --reload
```

### Generering af PDF/DOCX review-artefakter

For at generere DOCX og PDF for alle skabeloner (inkl. minimal/normal/edge profiler for kompatibilitetssættet) til manuel visuel inspektion uden for Git:

```bash
mkdir -p /tmp/m7-pdf-review && chmod 777 /tmp/m7-pdf-review
docker run --rm -v $(pwd):/workspace -v /tmp/m7-pdf-review:/tmp/m7-pdf-review -e UV_PROJECT_ENVIRONMENT=/tmp/venv -w /workspace document-builder:0.1.0 uv run python scripts/generate_review_artifacts.py
```

Resultater og `manifest.txt` / `manifest.json` findes i `/tmp/m7-pdf-review/`.

---

## Licens, herkomst og tredjepart

### Projektlicens
Projektmateriale skabt til Document Builder er udgivet under [Apache License 2.0](LICENSE). Dette omfatter:
- Python-kildekode og applikationslogik i `src/`
- Web UI-skabeloner, CSS og front-end-filer
- Drifts- og deployment-konfiguration (`Dockerfile`, `compose.yaml`, `Caddyfile`)
- Validerings- og hjælpescripts i `scripts/`
- Testsuiter og syntetiske testprofiler i `tests/`
- Projektdokumentation i `docs/` og markdown-vejledninger
- Deklarative `TemplatePackages` (`template.yaml`) og layout-skabeloner (`document.docx`)
- Hashøj IF-referencemateriale skabt som del af dette projekt

Se [`LICENSE`](LICENSE) for de fulde licensvilkår.

### Tredjepartssoftware og afhængigheder
Projektlicensen gælder udelukkende materiale skabt for Document Builder og omlicenserer ikke eksterne tredjepartskomponenter. Tredjepartssoftware, container-basis-images og afhængigheder bevarer deres respektive ophavsret og upstream-licenser.
- Se [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) for en fortegnelse over centrale runtime-komponenter (herunder Carlito-skrifttypen under SIL OFL 1.1, LibreOffice under MPL 2.0 med yderligere open source-komponenter, samt Caddy under Apache 2.0) og Python-afhængigheder.

### Herkomst (Provenance)
Det medfølgende Hashøj IF-referencemateriale i dette repository blev udviklet specifikt gennem Document Builder-projektets workflow som en komplet referenceimplementation (HIF-01 til HIF-21). Materialet er ikke importeret eller kopieret fra eksterne kommercielle skabeloner, andre foreningers proprietære dokumentsamlinger eller tredjeparts skabelonbiblioteker.

### Navne og varemærker
Navne og kendetegn tilhørende organisationer forbliver deres respektive ejeres ejendom. Brugen af Hashøj IF-navnet i dette repository tjener udelukkende til at identificere den medfølgende referenceimplementation. Projektlicensen indebærer ingen godkendelse eller anbefaling af afledte produkter fra Hashøj IF's side.
