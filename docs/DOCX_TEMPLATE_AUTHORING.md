# Retningslinjer for DOCX-skabelonforfatning (Template Authoring)

Denne vejledning beskriver regler og bedste praksis for konvertering og opbygning af `TemplatePackages` i Document Builder.

---

## 1. Mappestruktur for en TemplatePackage

Hver dokumenttype oprettes som en selvstændig pakke under `templates/<template_id>/`:

```text
templates/
  example-template/
    template.yaml     # Autoritativ datakontrakt, wizard-trin, felter, validering
    document.docx     # Word-layout og docxtpl-pladsholdere
```

---

## 2. `template.yaml` regler

1. **Metadata**:
   - `id`: Unikt, lowercase kebab-case (f.eks. `role-description`, `task-card`).
   - `version`: Heltal `>= 1`.
   - `enabled`: `true` (eller `false` under udvikling).
   - `title`, `category`, `description`: Ikke-tomme strenge.
2. **Wizard-trin (`steps`)**:
   - Gruppér felter i et overskueligt antal logiske domæneorienterede trin (`basic_info`, `tasks`, `contact`, etc.). Antallet af trin afgøres af dokumentets naturlige struktur; undgå både ét kæmpe trin og unødige et-felts trin.
   - Angiv sigende `title` og eventuel `description` for hvert trin.
3. **Feltdefinitioner (`fields`)**:
   - `id`: Semantisk lowercase snake_case (f.eks. `role_name`, `task_steps`).
   - `type`: `text`, `textarea`, `number`, `date`, `select`, `radio`, `checkbox`, `multiselect`, `repeater`, `info`.
   - `format`: Kun tilladt for `text` (`email`, `tel`, `url`).
   - `info`: Bruges til vejledning eller privatlivsoplysninger (`variant: privacy`). Kommer **aldrig** i render-konteksten og må **ikke** bindes i DOCX.
   - `checkbox`: Kan tildeles `purpose: acknowledgement` eller `purpose: consent` ved specifikke bekræftelser.
4. **Betingede felter (`show_when`)**:
   - Syntaks: `show_when: { field: <target_id>, equals: <value> }` (eller `not_equals`, `in`, `not_in`).
   - Inaktive felter udelades automatisk fra render-konteksten.
5. **Repeaters**:
   - Angiv `type: repeater`, `min_items`, `max_items` og `fields: [...]`.

---

## 3. `document.docx` regler & docxtpl-bindinger

1. **Pladsholdere**:
   - Skalare felter: `{{ field_name }}`
   - Repeater-børn: `{{ item.child_field }}` (eller `{{ loop.index }}` for rækkenummer)
   - Multiselect-elementer: `{{ item }}`
2. **Tabelløkker (Strukturelle tags)**:
   - For gentagne tabelrækker anvendes dedikerede kontrolrækker til `docxtpl`'s strukturelle rækketags, konceptuelt:
     ```text
     {%tr for item in repeater_name %}
     <data-række med felter som {{ item.child }}>
     {%tr endfor %}
     ```
   - De strukturelle kontrolrækker fjernes automatisk af `docxtpl` under rendering, så kun de genererede datarækker fremgår af det færdige dokument.
   - Strukturelle tags skal overholde projektets og `docxtpl`'s regel om ét tag pr. strukturel enhed (ingen blanding af dataindhold og `{%tr ... %}` i samme kontrolrække).
3. **Betingede sektioner**:
   - Enkle betingelser: `{% if field_name %}` ... `{% endif %}`
4. **XML-Run integritet**:
   - Undgå at Word splitter Jinja-tags på tværs af flere XML-runs (`<w:r>`). Indtast tags samlet eller opret dem programmatisk via `python-docx` for at garantere ren XML.
5. **Forbudte konstruktioner**:
   - Ingen custom filters, macroer, Python-funktioner, beregninger eller vilkårlig Python-kode i Word-skabelonen.

---

## 4. Testprofiler

Hver skabelon forsynes med tre testprofiler under `tests/compatibility/profiles/<template_id>/`:

- **`minimal.yaml`**: Indeholder udelukkende påkrævede (`required: true`) felter.
- **`normal.yaml`**: Realistiske, men fuldt ud fiktive eller syntetiske testdata.
- **`edge.yaml`**: Grænseværdier, lange tekster, danske tegn (`æ, ø, å`), XML-tegn (`<, >, &`) og Jinja-lignende tekststrenge (`{{ test }}`).

Repositoryets medfølgende Hashøj IF-referencepakke benytter tilsvarende `hif-`-præfikserede skabelon-ID'er og fiktive foreningsscenarier som referenceimplementation.
