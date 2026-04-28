# Conduction Services-model — tarievenkaart

Dit document beschrijft hoe Conduction Services factureert: projectmatige activiteiten (maatwerk-ontwikkeling, consultancy, training) die op uurtarief of per dagdeel worden afgerekend. Parallel aan [`support-model.md`](./support-model.md), dat ons Support-abonnement beschrijft (per app × per user × per jaar).

> **Brand-context (per 2026-04-28):** Services worden contractueel geleverd door **Conduction** (de juridische entiteit). Op de **`connext.conduction.nl`**-site verschijnt Services als een discrete sectie/footer-pagina met de melding *"Services worden geleverd door Conduction, de bouwer van ConNext."*. De tarieven en het model in dit document zijn ongewijzigd door de ConNext-rebrand — alleen de positionering op de website verschuift: Services is nu een service rondom het ConNext-ecosysteem, geleverd door Conduction.

**Kernverschil met Support:**

| | Support | Services |
|---|---|---|
| **Wanneer** | Doorlopend (abonnement) | Projectmatig / op afspraak |
| **Wat** | Helpdesk + proactieve telemetry-monitoring | Maatwerk-dev, consultancy, training, certificering |
| **Facturering** | Per app × per user × per jaar | Uurtarief × gewerkte uren (of per dagdeel bij training) |
| **Tiers** | Standard / Premium | Rol-afhankelijk (development / consultancy) |
| **Vooruitbetaling** | Ja (jaarlijks) | Optioneel (strippenkaart met korting) |

Een klant kan Services afnemen met of zonder Support. Beide zijn optioneel.

---

## Uurtarieven

Twee rollen, twee tarieven. Het tarief wordt bepaald door het type werk, niet door de persoon — één ontwikkelaar die een uur architectuur-advies geeft, factureert dat uur als consultancy.

| Rol | Uurtarief | Wat het dekt |
|---|---|---|
| **Development** | **€125 / uur** | Code schrijven, bugs fixen, features bouwen, tests, code-reviews, integraties implementeren, data-modellen bouwen |
| **Consultancy** | **€150 / uur** | Architectuur-advies, oplossings-ontwerp, workshops (niet-training), begeleiding bij strategische keuzes, implementatie-begeleiding, audits, second opinion, pre-sales-advies |

Tarieven zijn **ex. BTW**, **exclusief reistijd** (separaat indien van toepassing), en **exclusief reis- en verblijfkosten** (op basis van werkelijke kosten).

### Waarom dit tarief-verschil?

- **Development** is uitvoerend werk: de output is code, tests, documentatie. Reproduceerbaar, aftoetsbaar, duidelijk begrensd.
- **Consultancy** is denk-werk: de output is een keuze, een plan, een advies. Vraagt bredere expertise en draagt meer verantwoordelijkheid. Daarom 20% hoger tarief.

Klanten die twijfelen welke rol relevant is: wij geven vooraf een inschatting. In de praktijk bestaan veel projecten uit een mix — bv. een discovery-fase op consultancy-tarief gevolgd door een implementatie-fase op dev-tarief.

## Strippenkaart

Voor klanten met regelmatige behoefte aan Services bieden we een **strippenkaart-model** met korting bij vooruitbetaling.

| Variant | Bedrag vooraf | Korting | Effectief tarief (Dev) | Effectief tarief (Consultancy) |
|---|---|---|---|---|
| **Strippenkaart** | **€15.000** (ex. BTW) | **10%** | €112,50 / uur | €135 / uur |
| **Maatwerk-strippenkaart** | Op aanvraag (>€30.000) | Op aanvraag | Per offerte | Per offerte |

**Hoe werkt het:**

- Klant betaalt €15.000 vooraf
- Conduction schrijft uren af op deze pot tegen het verlaagde tarief
- Rekenvoorbeeld: €15.000 / €112,50 = **133 uur development** óf €15.000 / €135 = **111 uur consultancy** (of een mix)
- Restwaarde is geldig **12 maanden** vanaf aanschaf
- Elk uur wordt gerapporteerd: wie, wat, wanneer, tegen welk tarief, hoeveel rest
- **Bij uitputting:** klant kan bijkopen óf terugvallen op standaardtarief voor losse uren

**Wanneer is het interessant?**

- Je verwacht >100 uur werk in een jaar
- Je wil flexibiliteit (mix van dev + consultancy, ad hoc aanvragen zonder nieuwe offerte)
- Je hebt een jaarlijks budget dat je liever in één keer wegzet dan per factuur

**Wanneer liever standaardtarief?**

- Eenmalig project met afgebakende scope (dan gewoon vast-prijs of uurtarief-op-project-basis)
- <100 uur verwachting in een jaar
- Geen cash-flow-ruimte voor vooruitbetaling

## Training

Conduction verzorgt training over onze apps en het bredere Nextcloud-ecosysteem. Twee leveringsvormen met verschillend prijsmodel.

### Fysieke training (betaald)

Training op locatie — bij de klant of op een afgesproken trainingsplek.

**Eenheid:** dagdeel van **4 uur on-site lestijd**.

**Factuur-basis:** 8 uur per dagdeel (4 uur lestijd + 4 uur voorbereiding en verwerking).

**Waarom 8 uur per dagdeel en niet 4?**

Een goede training vraagt evenveel voorbereiding en nabehandeling als lestijd. Voorbereiding: materiaal op maat maken, demo-omgeving klaarzetten, klant-specifieke voorbeelden opstellen. Verwerking: vragen beantwoorden na afloop, hand-outs afronden, terugkoppeling verwerken. Factureren van alleen de lestijd zou neerkomen op het weggeven van die helft — dat doen we niet.

**Prijs per dagdeel:**

| Type trainer | Uren × tarief | Totaal per dagdeel |
|---|---|---|
| **Development-training** (technisch, hands-on code) | 8u × €125 | **€1.000** |
| **Consultancy-training** (functioneel, architectuur, processen) | 8u × €150 | **€1.200** |

**Gebruikelijke formats:**

- **Halve dag** (1 dagdeel, 4u lestijd): €1.000–€1.200
- **Volle dag** (2 dagdelen, 8u lestijd): €2.000–€2.400
- **Meerdaagse training**: kan met korting — op offerte

**Reis- en verblijfkosten:** apart gefactureerd op basis van werkelijke kosten (kilometers, OV, eventuele overnachting).

**Groepsgrootte:** geen harde limiet, maar >12 deelnemers vraagt om aangepaste werkvorm. Voor groepen van 15+ adviseren we twee trainers (prijs navenant).

### Online training (gratis)

Online trainingen zijn **gratis te volgen**. Dat past bij ons open-source-verhaal: kennisdeling hoort niet achter een paywall.

**Waar:** zelf-doorloopbaar materiaal via `docs.conduction.nl` / opgenomen webinars / live-online-sessies (aangekondigd via blog/nieuwsbrief).

**Wat zit erin:**

- Intro-cursussen per app (OpenRegister, OpenCatalogi, ...)
- Bredere onderwerpen: Common Ground-implementatie, NL Design integratie, API-first architectuur
- Hands-on labs met een publieke demo-omgeving

**Waarom gratis:**

- Ontmoedigt géén adoptie (geld mag nooit een reden zijn om niet te leren over onze apps)
- Vergroot de gebruiker-basis → meer kans op Support-abonnement of Services-opdrachten
- Congruent met het "penny-wise" merkwaarde in [`BRAND.md`](../../BRAND.md)

**Kwaliteits­beperking:** omdat online gratis is, is er géén individuele begeleiding of 1-op-1-interactie. Daar is fysieke training (of consultancy-uren) voor.

### Certificering (prijs-variabel)

Voor mensen die hun kennis formeel willen aantonen bieden we **certificering**: een proctored examen dat een officieel Conduction-certificaat oplevert.

**Belangrijk:** de training zelf is gratis (online). Het examen en het certificaat zijn betaald. Dit patroon volgt grote open-source-organisaties: Linux Foundation, Red Hat, Cloud Native Computing Foundation — allemaal gratis leermateriaal, betaalde certificering.

**Prijs:** **afhankelijk van het certificaat**.

Tarieven per certificaat worden gepubliceerd op de certificerings-pagina (niet in dit document, want ze kunnen verschillen per examen-type, per diepgang, per doelgroep). Verwachte range: **€150–€500 per certificaat**, vergelijkbaar met entry-level Linux Foundation (LFCS €395) en mid-level Nextcloud Certified Engineer-achtige examens.

**Geldigheid:** certificaten zijn 3 jaar geldig (gebruikelijk in deze industrie). Herkeuring tegen gereduceerd tarief.

**Open vraag:** welke certificeringen bieden we concreet aan? Eerste kandidaten:

- **Conduction Certified App User** — basis-gebruiker voor één of meerdere core apps
- **Conduction Certified Integrator** — voor IT-ers die apps in eigen omgeving deployen en integreren
- **Conduction Certified Solution Architect** — voor oplossings-ontwerpers die Conduction-stacks samenstellen (WOO, registers, zaakafhandeling)

Inhoud en precieze prijzen te bepalen tijdens de certificerings-uitrol.

## Totale Services-propositie — samengevat

| Leveringsvorm | Prijs | Beschikbaar |
|---|---|---|
| **Losse uren — Development** | €125 / uur | Doorlopend |
| **Losse uren — Consultancy** | €150 / uur | Doorlopend |
| **Strippenkaart** (€15K vooraf, 10% korting) | €112,50 / €135 per uur | Doorlopend |
| **Fysieke training — Development** | €1.000 / dagdeel (4u les + 4u voorbereiding) | Op afspraak |
| **Fysieke training — Consultancy** | €1.200 / dagdeel | Op afspraak |
| **Online training** | **Gratis** | `docs.conduction.nl` + geplande webinars |
| **Certificering** | €150–€500 per certificaat (indicatief) | In ontwikkeling |

Alle prijzen **ex. BTW**. Reis-/verblijfkosten separaat. Grotere projecten (>€30K) en maatwerk-tier-Support (24/7, kortere responstijden dan Premium) worden per offerte afgeprijsd op basis van deze tarieven.

## Services-pagina op de website

URL: **`/services`** op `connext.conduction.nl`. Linkt vanuit footer (niet hoofdnav — zie [`platform-benchmarks.md`](./platform-benchmarks.md) over waarom we bewust weg bewegen van dienstverlener-prominentie). Wél transparant indexeerbaar. Pagina-toon: *"Conduction levert Services rondom het ConNext-ecosystem"* — niet *"ConNext biedt Services"* (de Services-relatie is met Conduction-de-bedrijf, niet met de productbrand).

Zes secties, in deze volgorde:

### 1. Hero

- **H1 (NL):** *"Meer dan de apps — wij bouwen en leren ook mee wanneer je dat wilt."*
- **H1 (EN):** *"Beyond the apps — we can build and teach alongside you when you need it."*
- **Lead:** 2–3 regels die framen waarom Services bestaat (maatwerk, kennisoverdracht) én dat ze secundair zijn aan de gratis apps.

### 2. Wat biedt Services?

Vier blokken:

- **Development** — maatwerk-features, integraties, custom apps op OpenRegister
- **Consultancy** — architectuur-advies, implementatie-begeleiding, second opinion
- **Training** — fysiek op locatie, of online (gratis)
- **Certificering** — formeel Conduction-certificaat

Elk blok: één korte alinea + "Bekijk tarieven →" link naar de rate-card sectie.

### 3. Tarievenkaart

Full rate-card zoals hierboven. Disclaimer: *"Alle prijzen ex. BTW. Reiskosten separaat."* Duidelijke tabel-layout, geen nepwaardige "Vanaf"-verwarring.

Bovenaan een korte vergelijking met Support: *"Services is projectmatig. Zoek je doorlopende ondersteuning? Bekijk [Support →](/support)."*

### 4. Strippenkaart — uitgelegd

Eigen subsectie (niet alleen een regel in de tabel) omdat het een keuze-model is dat uitleg verdient. Inhoud:

- Waarom strippenkaart
- Hoe het werkt (vooruitbetaling, afboeken, rapportage)
- Wanneer interessant (>100 uur/jaar, flexibel gebruik)
- Wanneer liever niet (eenmalig project)

### 5. Training — details

Eigen subsectie omdat training (drie varianten: fysiek, online, certificering) meer uitleg vraagt dan in de tarievenkaart past. Inhoud:

- Fysieke training: waarom 8u per dagdeel, voorbeeld-formats (halve dag, volle dag, meerdaags), groepsgroottes
- Online training: wat is beschikbaar, waarom gratis
- Certificering: waarom betaald, welke certificaten beschikbaar, geldigheid

### 6. Contact & aanvragen

Contact-formulier of e-mail. Voor strippenkaart-aankoop: aparte flow (factuur + betaling vooraf). Voor trainings-aanvragen: datum, groepsgrootte, onderwerp, locatie in het formulier.

### Link naar Support

Onderaan: *"Ook op zoek naar doorlopende ondersteuning op je geïnstalleerde apps? Bekijk [Support →](/support)."*

## Wat de Services-pagina NIET moet bevatten

- Geen "vraag een offerte aan zonder prijzen te tonen" — wij zijn transparant
- Geen case-studies-as-hero (dat is voor de About-pagina)
- Geen "client logos"-wall die Services als consultancy-model weer prominent maakt
- Geen sales-urgency ("Plan dit kwartaal nog een training!" etc.)

## Relatie met onze andere proposities

| Wat | Voor wie | Hoe afgerekend | Voorbeeld |
|---|---|---|---|
| **Apps** | Iedereen | Gratis | OpenCatalogi installeren |
| **Support** | Klanten die zekerheid willen op geïnstalleerde apps | Abonnement (per app × per user × per jaar × 2 tiers) | Helpdesk, proactieve monitoring |
| **Services — Development** | Klanten die maatwerk willen | €125/uur (10% korting via strippenkaart) | Custom feature, integratie, dashboard |
| **Services — Consultancy** | Klanten die advies willen | €150/uur (10% korting via strippenkaart) | Architectuur-review, second opinion, implementatie-begeleiding |
| **Services — Fysieke training** | Organisaties die hun team willen opleiden | Per dagdeel (€1.000 dev / €1.200 consultancy) | Admin-training, gebruikers-training |
| **Services — Online training** | Iedereen | Gratis | Zelf-doorloopbaar materiaal, webinars |
| **Services — Certificering** | Mensen die kennis formeel willen aantonen | Per certificaat (€150–€500, indicatief) | Conduction Certified Integrator |
| **Partnerschap** | Nextcloud-leveranciers | Revenue share via Nextcloud | Leverancier verkoopt Support aan zijn klanten |

## Open vragen

- **Daadwerkelijke certificering-prijzen** — range €150–500 is indicatief. Per certificaat-type een echte prijs bepalen zodra de certificerings-uitrol start.
- **Welke certificaten komen er eerst?** Drie kandidaten hierboven genoemd; prioriteit en inhoud te bepalen.
- **Strippenkaart-alternatieven** — biedt Conduction ook grotere stappen aan (€30K, €50K met nog hogere korting)? Nu: op aanvraag / per offerte.
- **Internationale klanten** — euro-tarieven zijn duidelijk voor NL/BE/DE. Voor andere landen: zelfde tarief of afhankelijk van prijs-niveau? Nu: zelfde tarief, valuta-conversie door klant.
- **Reis-/verblijfkosten-regeling** — formaliseren: kilometervergoeding, OV-vergoeding, overnachtings-budget. Separaat document of onderdeel van de offerte?
- **Pro-bono-werk voor open-source-community** — soms zinvol (bijdrage aan standaarden, mentorschap). Wel/niet apart benoemen, en wie besluit?
