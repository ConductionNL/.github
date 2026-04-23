# Website Design Brief — www.conduction.nl (2026)

**Status:** Concept, ronde 1
**Laatste update:** 2026-04-23
**Thema:** `theme-conduction-2026`
**Doelstaat:** Bilingual (NL/EN), Docusaurus 3.x, product-first

## Waar deze brief op bouwt

**Foundation (company-wide):**

- [../BRAND.md](../BRAND.md) — merkwaardes, logo, kleurpalet, typografie, Apps-vs-Solutions terminologie
- [../DESIGN.md](../DESIGN.md) — rationale achter kleur/typo, tone-shift MKB-direct, visuele richting productbedrijf
- [../brand/tokens.json](../brand/tokens.json) — DTCG tokens (kleur + typografie, scope A)

**Content-appendix (website-specifiek, gemined uit onze intelligence-DB):**

- [`website/app-taglines.md`](./website/app-taglines.md) — tagline-library voor alle 11 core apps (NL + EN)
- [`website/solution-woo.md`](./website/solution-woo.md) — volledige WOO-solution-pagina als template voor andere solutions
- [`website/tone-samples.md`](./website/tone-samples.md) — NL tone-calibratie met drie registers en rewrite-recepten
- [`website/icon-library.md`](./website/icon-library.md) — iconen-bibliotheek-keuze (aanbevolen: Lucide)
- [`website/platform-benchmarks.md`](./website/platform-benchmarks.md) — uitgebreide deep-dive-analyse van Odoo en WooCommerce als app-platform-referenties; concrete IA-/layout-/CTA-patronen om over te nemen, aan te passen, of bewust níet over te nemen gegeven ons gratis + optionele-SLA-model
- [`website/sla-model.md`](./website/sla-model.md) — het Conduction SLA-model: twee paden (via Nextcloud-leverancier of rechtstreeks via app-admin-formulier), wat er concreet in de SLA zit (helpdesk + proactieve telemetry-ondersteuning), en wat dat betekent voor de SLA-pagina-structuur

**Deze brief beschrijft alleen het website-specifieke.** Alles wat Conduction-wide geldt (wie we zijn, hoe we eruitzien, welke woorden we gebruiken) staat in de foundation-documenten. Als iets uit deze brief toch company-wide blijkt, lift het terug naar BRAND.md of DESIGN.md.

---

## 1. Doel

Een nieuwe **www.conduction.nl** die bezoekers zo kort mogelijk naar de **Nextcloud app store** leidt. De site is de produkt-etalage van het Conduction-ecosysteem.

Wat deze site **niet** is:
- Geen corporate brochure (dienstverlener-site)
- Geen portal/login/dashboard (dat is Nextcloud zelf)
- Geen technische documentatie (dat is docs.conduction.nl)
- Geen e-commerce (apps zijn open source, installatie gaat via Nextcloud app store)

## 2. Strategische context

Context komt uit BRAND.md, kort herhaald:

- **Business-model shift.** Conduction beweegt van *consultancy (projecten, training, advies)* naar *productbedrijf (ecosysteem van Nextcloud-apps)*. Klanten kunnen ons gebruiken zonder ons te spreken.
- **Doelgroep-shift.** Van overheid-first naar MKB-first, met een eerlijke transitie: overheid is nog de meerderheid, MKB is het doel.
- **Tone-shift.** Van formele overheid-taal naar directe MKB-taal.

Dit samen maakt een **product-first, apps-in-de-hoofdrol, MKB-directe** site.

## 3. Doelgroepen

### Primair — MKB-beslisser / IT-lead (nieuw)

- Komt met een concreet probleem ("we moeten WOO-compliant worden", "we willen één registerplatform")
- Kent Conduction vaak **niet** vooraf — komt via Google op een solution-landingspagina
- Heeft een beperkt budget, wil zelf kunnen evalueren, geen consultancy-traject
- Leest scanbaar, klikt snel door, beslist in dagen-weken niet maanden

**Wat deze bezoeker nodig heeft:** heldere probleem-herkenning, concrete oplossing, directe installeer-route.

### Secundair — Overheid-beslisser / IT (bestaand)

- Kent Conduction al, heeft wellicht een lopende relatie of een project in gedachten
- Meer tijd, meer stakeholders, meer compliance-eisen (inkoop, BIO, ...)
- Wil zowel apps als ondersteuning (implementatie, training)

**Wat deze bezoeker nodig heeft:** apps duidelijk gepositioneerd, plus een discrete route naar Services/contact.

### Tertiair — Ontwikkelaar / Integrator

- Bouwt of integreert open source
- Komt vaak via GitHub of docs.conduction.nl
- Zoekt APIs, source code, contribution guides

**Wat deze bezoeker nodig heeft:** directe links naar GitHub, docs.conduction.nl, licenties. Niet veel meer.

## 4. Primaire taak & CTA-hiërarchie

De site heeft één primaire taak: **installeer een app vanuit de Nextcloud app store**. Alle andere CTA's zijn ondersteunend.

**Framing-principe — van "upgrade-druk" naar "download-druk".** Odoo en WooCommerce werken met upgrade/koop-druk (trial starten, kopen, upgraden). Bij ons is dat **download-druk**: elke pagina leidt naar één gratis, frictieloze actie — de app installeren. Geen trial-urgency, geen prijs-vergelijkingen, geen upgrade-nags. Primary button zegt altijd *"Install from Nextcloud app store"*, nooit *"Get started"* of *"Sign up"*. Zie [`website/platform-benchmarks.md §Van upgrade-druk naar download-druk`](./website/platform-benchmarks.md#van-upgrade-druk-naar-download-druk--de-kern-reframing) voor de volledige reframing.

| Rang | CTA | Waar |
|---|---|---|
| 1 | **Install from Nextcloud app store** | Elke app-pagina, homepage, solution-pagina's |
| 2 | **Try the demo** (indien beschikbaar) | App-pagina's |
| 3 | **Read the docs** (→ docs.conduction.nl) | App-pagina's, footer |
| 4 | **View on GitHub** | App-pagina's, footer |
| 5 | **Learn about the SLA** (discreet) | Footer, één homepage-strip |
| 6 | **Contact us** (discreet) | Footer |

**Regel:** CTA 1 is op elke app/solution-pagina zichtbaar zonder te scrollen. Andere CTA's mogen verderop. Contact en SLA-leren staan in de footer, niet in de hoofdnavigatie. **Géén** add-to-cart-achtige UI, **géén** urgency-tactics, **géén** pricing-pagina in de hoofdnav.

**SLA is géén conversiepunt op de website.** Het aanvragen van een SLA gebeurt buiten onze site — óf via de Nextcloud-leverancier van de klant (pad 1), óf via een formulier in de admin-instellingen van de geïnstalleerde app zelf (pad 2). Onze site *legt uit* dat de SLA bestaat en hoe je 'm krijgt, maar bevat geen shopping-cart. Zie [`website/sla-model.md`](./website/sla-model.md) voor de volledige uitleg.

## 5. Information Architecture

### Hoofdnavigatie (header)

1. **Apps** — de app-catalogus
2. **Solutions** — probleem-georiënteerde landingspagina's (WOO, registers, zaakafhandeling, ...)
3. **About** — wie we zijn, waardes, team
4. **Docs** (extern, → docs.conduction.nl)
5. **GitHub** (extern, → github.com/ConductionNL)
6. *(taalwisselaar NL/EN)*

### Footer

- SLA (pagina, niet in hoofdnavigatie) — "Meer zekerheid nodig? Zo werkt onze SLA."
- Services (pagina, niet in hoofdnavigatie) — implementatie, training, maatwerk
- Contact
- Privacy / Legal
- GitHub, LinkedIn, andere social
- Taalwisselaar (tweede plek, naast header)

### Sitemap

```
/                                        homepage
/apps                                    app-catalogus
/apps/{app-slug}                         app-detail
/solutions                               solution-catalogus
/solutions/{solution-slug}               solution-landing
/about                                   wie we zijn
/sla                                     (discreet; niet in hoofdmenu) — SLA uitleg + twee aanvraagpaden
/services                                (discreet; niet in hoofdmenu) — implementatie, training, maatwerk
/contact                                 contactformulier
/404                                     fallback

[per taal: /nl/... en /en/...]
```

## 6. Pagina-types

### 6.1 Homepage

**Job:** in ≤ 10 seconden duidelijk maken wat Conduction is, welke apps bestaan, en hoe je verder komt.

Structuur van boven naar beneden:

- **Hero** — korte pitch ("We bouwen een ecosysteem van Nextcloud-apps voor MKB en overheid") + primaire CTA ("Browse our apps" → /apps) + secundaire CTA ("Solve a problem" → /solutions). Visueel: app-screenshot of hexagon-compositie, geen teamfoto.
- **Featured apps** — 4–6 core apps in kaartvorm met hexagon-logo, naam, tagline, "Install" CTA
- **Top solutions** — 3–4 meest relevante solutions als teasers met "Read more" naar solution-pagina
- **Ecosystem-strip** — één beeld dat het verband toont tussen apps (interconnected, hexagon-rooster)
- **Proof** — installed-count, gemeenten/organisaties die ons gebruiken, GitHub-sterren
- **Footer** — zie boven

**Geen** op de homepage: teamfoto, mission-statement lang verhaal, "onze diensten"-sectie, blog-feed als hero.

### 6.2 App-catalogus (`/apps`)

**Job:** alle apps tonen met voldoende structuur dat een bezoeker snel de juiste vindt.

- Filter/sorteer: op solution, op status (stable/beta/experimental), op NLDS-compliance, op deployment-model
- Grid of list view, toggleable
- Per app-kaart: hexagon-logo, naam, tagline, status-badge, CTA "View details"
- Lege state (bv. na filter): "Ontbreekt een app die je zoekt? Dien een verzoek in" → GitHub link
- Sticky filter op desktop; modal filter op mobile

### 6.3 App-detail (`/apps/{slug}`)

**Job:** één app volledig uitleggen en installeren.

Structuur:

- **Hero** — hexagon-wrapped app-logo, naam, tagline, status-badge, primaire CTA **"Install from Nextcloud app store"**, secundaire CTA "View demo" / "Read docs"
- **Screenshots** — 3–5 schermen, carousel of grid
- **Wat doet het?** — 2–3 alinea's MKB-taal, concreet
- **Voor welke solutions?** — links naar relevante solution-pagina's
- **Integreert met** — andere apps in het ecosysteem (klikbare mini-kaarten)
- **Technische facts** — licentie, versie, NLDS-compliance, Nextcloud-versie, GitHub-link, docs-link
- **Testimonials / use-cases** (optioneel, komt later als content er is)
- **CTA-repeat** — "Install from Nextcloud app store"

### 6.4 Solution-catalogus (`/solutions`)

**Job:** wie niet weet welke app, maar wel een probleem heeft, hier vanaf laten starten.

- Probleemgerichte categorieën (transparantie & WOO, data & registers, zaakafhandeling, organisatie-management, softwarecatalog, ...)
- Per categorie een korte beschrijving en kaarten naar solution-landingspagina's

### 6.5 Solution-landing (`/solutions/{slug}`)

**Job:** SEO-magneet voor probleemzoekers ("WOO compliance software", "open source zaakafhandeling"); vertaalt het probleem naar een app-stack.

Structuur:

- **Hero** — probleem in MKB-taal ("WOO-compliant worden is verplicht sinds 2022. Hier is hoe je het aanpakt.")
- **Wat is dit probleem?** — didactische uitleg, ~300 woorden, voor wie het nog niet kent
- **Hoe los je het op?** — beschrijving van de aanpak
- **De app-stack** — welke apps je nodig hebt, in welke rol (visualisatie: stack-diagram)
- **CTA** — "Install the stack" (link naar app-catalogus gefilterd op deze solution, of per-app links)
- **Testimonials / cases** (optioneel)
- **FAQ** (optioneel) — SEO-voer

### 6.6 About (`/about`)

**Job:** wie is Conduction, waar staan we voor, wie zit erachter.

Structuur:

- Missie en waardes (korte versie van BRAND.md)
- Team (foto's en rollen horen hier, niet op de homepage)
- Manifest / Common Ground-positie / open-source filosofie
- Roadmap-link (indien publiek)
- Contact-CTA

### 6.7 SLA (`/sla`)

**Job:** voor wie meer zekerheid wil dan "installeer en draai zelf". Niet in hoofdmenu, wel in footer, wel indexeerbaar. Geen bestelformulier — wel een heldere uitleg van de twee paden waarop je een SLA kunt krijgen (via je Nextcloud-leverancier of rechtstreeks via het formulier in de app-admin-instellingen).

Volledige structuur (7 secties) en inhoudelijke invulling: zie [`website/sla-model.md`](./website/sla-model.md). Kort:

- Wat is onze SLA? (hero, korte uitleg)
- Wat zit erin? (helpdesk + proactieve telemetry-ondersteuning)
- Hoe vraag ik 'm aan? (pad 1 via leverancier, pad 2 via app-admin-formulier)
- Voorwaarden (hoog-over)
- Kosten (geen prijslijst — "neem contact op voor een offerte")
- FAQ (6–8 vragen)
- Contact-CTA (discreet)

### 6.8 Services (`/services`)

**Job:** voor wie specifiek naar implementatie-hulp, training of maatwerk zoekt. Niet in hoofdmenu, wel in footer. Onderscheid met SLA: SLA is doorlopende support op geïnstalleerde apps; Services zijn projectmatige activiteiten (implementatie-traject, training-sessie, maatwerk-ontwikkeling).

Structuur:

- "Het ecosysteem staat centraal, maar we helpen je graag ook met implementatie, training of maatwerk"
- Services: implementatie-ondersteuning, training, maatwerkadvies, integratie-projecten
- Voor welke doelgroep (voornamelijk overheid, maar open voor MKB)
- Contact-formulier of -CTA
- Link naar SLA-pagina als "Ook op zoek naar doorlopende support? Bekijk de SLA."

### 6.9 Contact (`/contact`)

- Formulier (naam, organisatie, e-mail, onderwerp-categorie, bericht)
- E-mail, telefoon (indien)
- GitHub discussions, Slack/Discord (indien)
- Routebeschrijving/adres alleen als we een publiek kantoor hebben dat bezoekers verwelkomt

### 6.10 404

- Speelse hexagon-illustratie ("lost in the grid")
- Zoekveld
- Links naar /apps, /solutions, homepage
- Primary CTA: terug naar homepage

## 7. Content types

### App

Voor alle 11 core apps staan naam, categorie en tagline (NL + EN) klaar in [`website/app-taglines.md`](./website/app-taglines.md) — gemined uit de intelligence-DB (top-features per app). Designer kan hieruit direct werken bij de app-catalogus-mock.

| Veld | Type | Verplicht |
|---|---|---|
| name | string | ja |
| slug | string | ja |
| tagline | string (1 regel) | ja |
| description | markdown | ja |
| logo_hexagon | SVG-pad | ja |
| screenshots | array of image + caption | aanbevolen |
| demo_url | URL | optioneel |
| nextcloud_appstore_url | URL | ja |
| github_url | URL | ja |
| docs_url | URL | ja |
| status | enum (stable, beta, experimental) | ja |
| nldesign_compliant | boolean | ja |
| latest_version | string | ja |
| licence | string (SPDX) | ja |
| solutions | array of solution-refs | optioneel |
| integrates_with | array of app-refs | optioneel |

### Solution

Een volledig uitgewerkte WOO-solution-pagina (inclusief hero, probleem-uitleg, aanpak, app-stack-tabel, FAQ en SEO-metadata) staat als **template** in [`website/solution-woo.md`](./website/solution-woo.md). De andere solutions volgen diezelfde structuur. Bron: 1.031 NL-tenders + 5.992 Woo-requirements uit onze intelligence-DB.

| Veld | Type | Verplicht |
|---|---|---|
| name | string | ja |
| slug | string | ja |
| tagline | string | ja |
| problem_statement | markdown | ja |
| description | markdown | ja |
| app_stack | array of `{app, role}` | ja |
| seo_keywords | array of strings | aanbevolen |
| faq | array of `{q, a}` | optioneel |
| testimonials | array | optioneel |

### Optioneel voor later — Customer Story, Blog Post / Pulse

Niet voor MVP. Later toevoegen als er content is.

## 8. Tone & voice — website-specifiek

Foundation: zie [../DESIGN.md](../DESIGN.md#tone--visuele-richting--implicaties-van-de-positioneringsshift). Kalibratie met authentieke NL-tender-taal staat in [`website/tone-samples.md`](./website/tone-samples.md) — drie registers herkennen plus rewrite-recepten van overheid-taal naar Conduction-taal. Website-aanvullingen:

- **Lead met het resultaat, niet het proces.** *"Installeer in 2 minuten"* > *"Onze implementatie-methodologie"*.
- **Gebruik cijfers.** *"100+ gemeenten"*, *"bespaart 20 uur per maand"*. Vage superlatieven zijn verboden.
- **Open-source trots zichtbaar.** GitHub-link op elke app-pagina, licentie prominent, "Contribute" als optie voor ontwikkelaars.
- **Ecosysteem-framing.** *"Deze app werkt alleen, maar het beste met X en Y"*. Verkoop niet alleen de losse app, verkoop ook het samenspel.
- **Geen consultancy-taal.** Verboden woorden: *digitale transformatie*, *ketensamenwerking als werkwoord*, *waardevolle inzichten*, *samen werken we aan*. Als je zo'n zin schrijft, schrap hem en herformuleer naar concreet resultaat.
- **Humor mag.** 404-pagina, micro-copy in formulieren, een knipoog hier en daar. Niet bezwarend professioneel.

## 9. Visuele richting — website-specifiek

Foundation: zie [../DESIGN.md](../DESIGN.md#visuele-richting). Website-aanvullingen:

- **Hero's tonen software, niet mensen.** Uitzondering: About-pagina.
- **Hexagon als terugkerend element.** App-logo's altijd in hexagon-wrapper. Sectiedividers of illustratie-elementen mogen hexagon-patronen gebruiken.
- **Kleurproportie.** ~70% wit, 20% cobalt, 8% oranje, 2% rood (zie BRAND.md). Hero mag cobalt-fond hebben; body is overwegend wit.
- **Typografie.** Figtree voor alles behalve code; IBM Plex Mono voor code-snippets en version-strings.
- **Illustraties** in cobalt-palet met oranje highlights. Eén stijl door de hele site; geen mix van 3D-renders, flat-illustrations en isometrische diagrammen door elkaar.
- **App-screenshots** met lichte omlijsting (1–2px cobalt) of schaduw voor diepte. Niet tilt-geroteerd; strak recht.
- **Geen** stockfoto's. Geen 3D-renders van abstract netwerken. Geen "diverse team werkt samen"-foto's.
- **Iconen:** [Lucide](https://lucide.dev) als standaard-bibliotheek (ISC, lijn-iconen, peer-group-adoptie). Volledig afwegingskader en implementatie-notities in [`website/icon-library.md`](./website/icon-library.md).

### Referentie-sites (positief + anti)

Kritische invoer voor de designer om de **toon en sfeer** te kunnen ankeren. Zonder deze referenties produceert een one-shot een gemiddelde-van-alles-ontwerp dat nergens helemaal op past.

Bron: onze competitive-intelligence database (`concurrentie-analyse/intelligence.db` en uitgebreidere Postgres — 1.088 gecatalogeerde competitors met relatie `competitor` / `ally` / `initiative`, binnen een bredere pool van ~32K GitHub-repos en ~17K organisaties). De onderstaande selectie is een handmatige curatie uit die data — vijf positieve referenties die elk een ander aspect raken, plus twee anti-referenties als duidelijke "niet dit".

#### Positief — vijf richtingen om naartoe te bewegen

| Site | Relatie in DB | Wat we ervan overnemen |
|---|---|---|
| [**Nextcloud**](https://nextcloud.com) | ally | **Tonale aansluiting + app-store-model.** We leven letterlijk in hun ecosysteem en onze bezoekers komen (of zouden moeten komen) daar vandaan. Bij elke design-beslissing de sanity-check: "zou deze pagina naast Nextcloud's eigen site werken?" Hun app-store-IA is wat wij voortzetten. |
| [**Decidim**](https://decidim.org) | initiative | **Civic-OSS-toon en solution-first-IA.** AGPL, Barcelona, multilingual, government-adjacent. Hun solution-pagina's leggen echt een maatschappelijk probleem uit voor ze naar de software gaan — exact het patroon voor onze WOO/zaakafhandeling-landingspagina's. Dichtst-bij-buurman op missie. |
| [**Supabase**](https://supabase.com) | competitor (openregister) | **Gouden standaard voor OSS-productbedrijf + ecosystem-catalogus.** Hun Extensions-sectie is structureel vergelijkbaar met onze apps-catalogus. Open source plus commercial add-ons — net als ons model (apps + ondersteunende services). Sterke typografische hiërarchie, dichtheid zonder drukte. |
| [**Backstage**](https://backstage.io) | competitor (internal developer portal) | **Ecosystem- en plugin-framing.** Spotify's portal framework is expliciet "core + plugins = ecosystem". Onze apps zijn onze plugins. Meest directe conceptuele peer voor het verhaal "install what you need uit een groeiende catalogus". Het model dat zij verkopen, bouwen wij. |
| [**PostHog**](https://posthog.com) | competitor (marketing-suite) | **Persoonlijkheid zonder corporate-saaiheid.** Bewijst dat open-source niet zakelijk-droog hoeft. GitHub-trots zichtbaar, humor in microcopy, maar professioneel. MKB-vriendelijke toon. |

Twee observaties bij deze selectie:
- Geen van deze vijf is een traditionele NL-overheidsleverancier. Dat is bewust — de markt is gevuld met traditionele leveranciers (zie anti-referenties), en we willen juist *niet* zo ogen.
- **Decidim** is de enige EU/NL-aangrensde referentie. Als er tussen de designs een "te anglo-tech-SaaS" spanning ontstaat, trek dan richting Decidim's register.

#### Anti — twee sites waar we expliciet van wegbewegen

Classic NL-gov-vendor-sites: beleidsterrein-georiënteerde IA, corporate-blauw, stockfoto's van mensen in pakken, "vraag een demo aan"-flow, lange sales-cycles. Uit onze DB zijn dit de meest archetypische voorbeelden (beide `proprietary` / `subscription`, beide gericht op dezelfde NL-gov-afnemers die *wij* anders willen benaderen):

| Site | Relatie in DB | Waarom anti-referentie |
|---|---|---|
| [**PinkRoccade Local Government**](https://www.pinkroccadelocalgovernment.nl) | competitor (Sociaal Domein, CiVision Midoffice) | Prototype NL-gov-vendor-site: sector-gerangschikte IA ("beleidsterreinen"), corporate-blauwe stockfoto's, "neem contact op voor een offerte". Alles wat wij *niet* zijn. Wij installeer-je-direct, zij verkoop-cycle. |
| [**BCT**](https://www.bct.nl) (Corsa ECM) | competitor (Corsa, GeoVacs VTH) | Traditionele document-management-vendor voor gemeentes. Enterprise-layout, dienstverlener-visual-language, geen spoor van "product eerst". Exact de look waar we in de tone-shift (BRAND.md / DESIGN.md) vanaf willen. |

#### Gebruiksinstructie voor de designer

- Positief-referenties zijn **aspect-bronnen**, geen copy-bronnen. Per ontwerpbeslissing: welk aspect is hier leidend?
- Als een mock "tussen PinkRoccade en Supabase" zit: altijd verder richting Supabase.
- Als een mock té developer-gericht wordt (docs-dichtheid, code-blokken overal): terug richting Nextcloud/PostHog om de MKB-toon te herstellen.
- Als een mock stoffig/overheidsformeel oogt: naar Decidim voor het civic-OSS-register; weg van PinkRoccade/BCT.
- De hexagon-wrapper en kobalt+oranje zijn *onze*. Geen enkel referentie-site heeft die — borrow structurele patronen, geen visual-brand-elementen.

## 10. Internationalisatie (bilingual NL/EN)

- **URL-structuur:** expliciete locale-prefix. `/nl/...` en `/en/...`. Root `/` redirect op basis van browser-taal.
- **Default-locale:** Nederlands (onze MKB-doelgroep zoekt in NL, WOO en zaakafhandeling zijn NL-termen).
- **Volledige vertaling:** elke pagina beschikbaar in beide talen. Geen mengvorm (deels NL, deels EN).
- **hreflang-tags** en canonical-URL's per pagina voor correct indexeren.
- **Taalwisselaar** zichtbaar in header (primair) en footer (secundair). Switch houdt de huidige pagina aan (niet terug naar homepage).
- **SEO-strategie per taal:**
  - **NL** — keywords rond WOO, zaakafhandeling, gemeente-software, Common Ground, NLDS, open source overheid. Primair SEO-doel.
  - **EN** — keywords rond Nextcloud apps, open source government, Dutch open source. Secundair, voor internationale community.
- **Content-management:** per-locale markdown-bestanden in Docusaurus, volgens [Docusaurus i18n](https://docusaurus.io/docs/i18n/introduction).

## 11. Accessibility

- **Target:** WCAG 2.1 AA minimum, AAA waar haalbaar (cobalt-op-wit haalt AAA makkelijk).
- **Keyboard-navigation** volledig werkend. Focus-states in oranje (KNVB), zichtbaar en contrasterend.
- **Semantic HTML:** `<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>`. Heading-hiërarchie correct (geen `<h1>` → `<h4>`-sprongen).
- **Alt-teksten** op alle afbeeldingen en app-logo's. Logo's krijgen `alt="{app-naam} logo"`, screenshots een beschrijvende alt-tekst.
- **Reduced-motion** respecteren (`prefers-reduced-motion`). Animaties zijn decoratief, nooit cruciaal voor begrip.
- **Taal-attributen:** `<html lang="nl">` of `"en"` per pagina, gemarkeerde anderstalige woorden met `<span lang="...">`.

## 12. SEO

**Primaire SEO-assets:** solution-landingspagina's. Daar investeren we content-gewicht.

- **Page-titles:** `{Probleem} — {Conduction oplossing}`. Bv. *"WOO-compliance met open source — Conduction"*.
- **Meta-descriptions** per pagina, handmatig geschreven, 140–160 tekens.
- **Structured data:** `SoftwareApplication` schema per app; `Article` of `FAQPage` schema per solution.
- **Sitemaps:** per locale. Automatisch via Docusaurus.
- **Performance-doel:** Lighthouse ≥ 90 op Performance, Accessibility, Best Practices, SEO. Mobile én desktop.
- **Core Web Vitals:** LCP < 2.5s, CLS < 0.1, INP < 200ms.

## 13. Success-metrics

### Primaire KPI's

- **Click-through naar Nextcloud app store** (per app + totaal). Dit is waar alles op afgerekend wordt.
- **Solution-page traffic uit organisch zoekverkeer** (per solution + totaal). SEO-succes.

### Secundaire KPI's

- **Time-to-click-to-app-store** — hoe snel vindt een nieuwe bezoeker de install-CTA. Lager is beter.
- **Bounce op app-detail** — bij hoge bounce: app-pagina overtuigt niet.
- **Terugkerende bezoekers** — MKB-beslissingen duren; meerdere bezoeken zijn normaal.

### Anti-metrics (bewust niet leidend)

- **Gemiddelde tijd op site** — niet het doel. We willen korte paden naar install.
- **Contact-form submissions** — welkom, maar niet de hoofdtaak van de site.

## 14. Out of scope

Voor MVP expliciet **niet**:

- User accounts, login, dashboards
- Betalingen, shop, licensing-flows (apps zijn open source, app store regelt het)
- Discussie-forum (→ GitHub Discussions)
- Blog / pulse (komt later als content er is)
- Customer stories (komt later)
- Interactieve demo-playground (komt later)
- Multi-brand (bv. white-label varianten van Conduction-apps)
- Analytics-dashboards zichtbaar voor bezoekers
- AI-chatbot / ask-me-anything

## 15. Implementatie-aanpak: design-first, Docusaurus-second

We bouwen **niet** direct in Docusaurus. Eerst ontwerp, dán implementatie. Dat houdt de design-discussie los van technische constraints en voorkomt dat Docusaurus-conventies ongevraagd het ontwerp sturen.

### Fase 1 — Design (nu, met Claude)

- **Artefacten:** statische HTML+CSS mocks per pagina-type
- **Fidelity:** pixel-accurate, alle breakpoints (mobile, tablet, desktop), werkende links *tussen* mocks, geen werkende backend
- **Stack voor mocks:** plain HTML + CSS (gebruik de tokens uit `brand/tokens.json` als CSS custom properties), optioneel een klein beetje JS voor filters/toggles. **Géén Docusaurus-afhankelijkheid in deze fase.**
- **Opslag:** `briefs/website/design/` (aparte subdirectory onder deze brief) — één HTML-bestand per pagina-type plus een gedeelde `styles.css` die de tokens leadt.
- **Iteratie:** per pagina-type gaan we door tot goedgekeurd. Homepage eerst, dan app-detail, dan solution-landing, dan de rest.
- **Levensduur:** deze mocks zijn *disposable* — ze zijn ontwerp-artefact, geen productie-code. Wanneer de Docusaurus-implementatie staat, mogen ze opgeruimd worden.

### Fase 2 — Docusaurus-implementatie (later)

- **Stack:** Docusaurus 3.x (upgrade van de 2.4.3 op docs.conduction.nl; versie-synchronisatie tussen de twee sites houden we aan). Zelfstandige Docusaurus-instantie; deelt tokens met docs-site maar niet dezelfde install.
- **Thema:** custom Docusaurus-thema dat de Conduction-tokens consumeert (CSS custom properties, fonts via self-hosted assets i.p.v. Google CDN om GDPR-redenen).
- **Content:** markdown met frontmatter per app en solution. Apps en solutions als content-plugin (eigen content-type via Docusaurus plugin-content-docs of aangepaste variant).
- **Deployment:** GitHub Pages (bestaande `gh-pages` flow uitbreiden, of een parallelle site).
- **Migratiepad:** HTML-structuur en CSS-tokens uit fase 1 hergebruiken; Docusaurus-routing, i18n en content-loading nieuw.

### Verwachte opdeling van werk

- Design-fase (fase 1): één pagina-type per sessie, iteratief, deze brief als anker.
- Implementatie-fase (fase 2): wanneer alle kritieke pagina-types zijn goedgekeurd. Geen harde planning; afhankelijk van design-voortgang.

## 16. Launch-scope (MVP)

### Core apps voor launch (11 stuks)

Uit [../../CLAUDE.md](../../CLAUDE.md) core-apps-lijst:

| # | App | Korte rol |
|---|---|---|
| 1 | **OpenRegister** | Foundation — de gedeelde datastore en schema-motor |
| 2 | **OpenCatalogi** | Catalogus-app, metadata-publicatie, WOO |
| 3 | **OpenConnector** | Integratie-motor, API-koppelingen |
| 4 | **DocuDesk** | Documentbeheer |
| 5 | **MyDash** | Dashboards en rapportages |
| 6 | **SoftwareCatalog** | Softwarecatalogus voor organisaties |
| 7 | **LarpingApp** | Larping-beheer (community-voorbeeld dat het ecosysteem laat zien) |
| 8 | **ZaakAfhandelApp** | Zaakafhandeling |
| 9 | **Procest** | Procesmanagement |
| 10 | **PipelinQ** | Pipeline-beheer |
| 11 | **NLDesign** | *Bijzondere positie* — dit is geen app maar een thema/integratie. Featured als "zo ziet Conduction er uit in Nextcloud", niet als op-zichzelf-staand product. |

### Featured solutions voor launch

Nader te bepalen op basis van SEO-onderzoek en huidige klantvragen. Eerste verwachte vijf:

1. **WOO-compliance** (OpenCatalogi + OpenConnector + DocuDesk)
2. **Organisatieregister** (OpenRegister + OpenCatalogi)
3. **Zaakafhandeling voor gemeenten** (ZaakAfhandelApp + OpenConnector)
4. **Softwarecatalogus / leverancier-inzicht** (SoftwareCatalog)
5. **Common Ground referentie-implementatie** (OpenRegister + OpenConnector + NLDesign)

Dit wordt bevestigd in een aparte session voordat solution-pagina's ontworpen worden.

## 17. Open vragen / vervolgbeslissingen

Deze noteren we maar lossen we niet nu op:

- **Apps-catalogus via OpenCatalogi (eat-our-own-dog-food)** — wij hebben een product dat federated data-catalogi publiceert (OpenCatalogi). De apps-catalogus op www.conduction.nl is per definitie zo'n catalogus. Overwegen: bouwen we de `/apps`-pagina als een OpenCatalogi-deployment (publiceer-vanuit-de-bron), waarbij de website zelf een live-demo is van wat OpenCatalogi doet? Voordeel: authenticiteit, demonstratie, Common Ground-congruentie. Nadeel: meer architectuur-complexiteit, koppelt website-uptime aan OpenCatalogi-runtime. **Besluit voor later** — eerst HTML+CSS-mock van de catalogus, dan bekijken of OpenCatalogi-rendering haalbaar en wenselijk is voor de implementatie-fase.
- **SLA in-app-formulier UX** — voor pad 2 (self-managed Nextcloud) zit het SLA-aanvraag-formulier in de admin-instellingen van elke Conduction-app. Dat is niet deze brief, maar vraagt om een aparte app-UI-brief met template en velden. Koppeling met ons CRM (PipelinQ?) ook openstaand.
- **Nextcloud-leveranciers-lijst** — welke leveranciers ondersteunen pad 1 van onze SLA? Nog op te stellen. Relevant voor de SLA-pagina.
- **Nextcloud app store koppeling** — directe deeplinks per app, of een embed-widget? Hangt af van wat de Nextcloud app store ondersteunt.
- **Demo-omgeving** — self-hosted op `demo.conduction.nl` met reset-na-24u, of gewoon screenshot-first en doorverwijzing naar docs?
- **Customer stories** — welke klanten mogen we noemen, per wanneer, met welke content?
- **Blog/pulse** — komt er een publieke blog, wie schrijft, welke cadence?
- **Docs migratie** — docs.conduction.nl staat op Docusaurus 2.4.3. Tegelijk upgraden naar 3.x, of volgtijdig?
- **Analytics-keuze** — Plausible, Matomo, of geen? Privacy-first is vereist.
- **Contact-stack** — eigen formulier + mailer, of integratie met bestaand CRM/helpdesk?
- **Team-content** — wie staat op de About-pagina, met welke rol-beschrijvingen, en hoe vaak actualiseren?

## 18. Changelog

| Datum | Wijziging | Door |
|---|---|---|
| 2026-04-23 | Initiële brief: product-first, apps-in-de-hoofdrol, bilingual NL/EN, Docusaurus als doelstack, design-first proces, 11 core apps als launch-scope | Brand-initiatief |
