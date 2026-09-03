# Kompatibilitetsprofiler (Testfixtures)

Dette bibliotek indeholder testfixtures i form af YAML-profiler (`minimal.yaml`, `normal.yaml`, `edge.yaml`) til automatiseret verifikation af validering, DOCX-rendering og PDF-konvertering.

## Syntetisk Datapolitik

- **Udelukkende syntetiske testdata**: Alle profiler indeholder udelukkende fiktive testdata skabt til automatiserede testformål.
- **Fiktive navne og kontaktpersoner**: Personnavne, kontaktpersoner og funktionsroller er syntetiske (f.eks. `Testperson A`, `Testperson B`, `Testperson Æ-Ø-Å`). Der må aldrig tilføjes reelle personoplysninger.
- **Reserverede e-maildomæner**: Alle e-mailadresser anvender officielt reserverede test- og eksempeldomæner (`example.com`, `example.org`, `example.net`).
- **Syntetiske telefonnumre og identifikatorer**: Telefonnumre (f.eks. `00 00 00 01`) og CVR/EAN-identifikatorer (f.eks. `00000000`) følger bevidst ikke-kontaktbare syntetiske mønstre, der overholder systemets formater.
- **Fiktive organisationer**: Eksterne virksomheder og organisationer i fixture-værdier er fiktive eksempler (f.eks. `Eksempel Kommune`, `Eksempel Leverandør A/S`, `Eksempel Fonden`). "Hashøj IF" optræder udelukkende som referenceforening for produktet.
- **Testformål og kanttilfælde**: Profilerne eksisterer for at afprøve tekniske kanttilfælde, herunder danske specialtegn (æ, ø, å), XML-tegnescaping, Jinja-syntaksbeskyttelse, multiline-tekster samt tabellayout og sideskift i DOCX og PDF.
- **Særlige hændelsesscenarier (f.eks. HIF-17)**: Hændelses- og skadescenarier i inaktive eller privatlivsbeskyttede skabeloner (såsom HIF-17) er rent fiktive testsituationer til validering af skabelonfunktionalitet og beskriver ingen virkelige personer eller hændelser.
