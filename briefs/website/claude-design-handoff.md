# Claude Design handoff-prompt

Dit document bevat de **kant-en-klare prompt** die je aan Claude Design (Claude gebruikt als website-designer) geeft om de eerste design-mock van www.conduction.nl te laten maken.

## Hoe te gebruiken

1. Start een nieuwe Claude-sessie in een repo die toegang heeft tot de `.github/` directory (of kopieer de relevante bestanden mee)
2. Paste de **Master-prompt** hieronder als eerste bericht
3. Claude Design zal alle documenten lezen en een homepage-mock produceren (statische HTML+CSS)
4. Itereer per pagina-type: eerst homepage tot goedgekeurd, dan app-detail, dan solution-landing, enzovoort

---

## Master-prompt — copy-paste deze

> Je bent de lead-designer van www.conduction.nl — de nieuwe marketing-site voor Conduction, een Nederlands open-source-productbedrijf dat een ecosysteem van Nextcloud-apps bouwt.
>
> Ik wil dat je een **statische HTML+CSS mock** maakt van de **homepage**. Geen React, geen build-stap, geen Docusaurus nog — puur `index.html` + `styles.css` met SVG-illustraties inline of als losse bestanden. Pixel-accuraat op desktop (1440px breed), tablet (768px) en mobile (375px). Gebruik echte content, geen lorem ipsum. Output in een dedicated folder: `briefs/website/design/homepage/`.
>
> Lees deze documenten **vóór je ook maar één regel CSS schrijft**, in deze volgorde:
>
> **Foundation (verplicht lezen, company-wide):**
> 1. `BRAND.md` — wie we zijn, wat we bouwen (ecosystem, niet consultancy), doelgroep (MKB-first, overheid in afbouw), Apps-vs-Solutions terminologie, Support- en Services-proposities
> 2. `DESIGN.md` — kleur-rationale (cobalt `#21468B` + KNVB-oranje `#F36C21` + vermiljoen `#AE1C28`), typografie (Figtree + IBM Plex Mono), tone-shift (MKB-direct, geen "u"/"toekomstbestendig"/"digitale transformatie"), hexagon als systematisch motief (altijd pointy-top, voor accenten niet containers)
> 3. `brand/tokens.json` — DTCG-tokens voor kleur + typografie (scope A). Gebruik deze als CSS custom properties — géén hardcoded hex-waardes in de mock.
>
> **Website-specifiek (verplicht lezen):**
> 4. `briefs/website.md` — de volledige website-brief: IA, pagina-types, content-types, CTA-hiërarchie (primair = "Install from Nextcloud app store"; download-druk niet upgrade-druk), homepage-structuur in 7 secties, navigation
> 5. `briefs/website/visual-motifs.md` — hexagon-catalogus (bullets, pagination, status, avatars, badges, dividers, timeline-kralen, empty-states), per-sectie-treatments, **gekozen illustratie-stijl A2 (flat-isometric hex-prism)**, Platform-overview-pattern voor homepage-hero
> 6. `briefs/website/app-taglines.md` — tagline per app (NL + EN) voor de apps-grid-sectie
> 7. `briefs/website/platform-benchmarks.md` — reframing "upgrade-druk naar download-druk", zeven patronen om over te nemen van Odoo/WooCommerce/Nextcloud, patterns om níet over te nemen
> 8. `briefs/website/support-model.md` — Support-pagina-structuur + pricing-tabel-structuur (placeholder-waardes, niet blootstellen in mock zonder disclaimer)
> 9. `briefs/website/services-model.md` — Services-tarievenkaart (dev €125, consultancy €150, strippenkaart, training, certificering)
> 10. `briefs/website/tone-samples.md` — NL tone-calibratie: drie registers herkennen, rewrite-recepten naar Conduction-copy
>
> **Referentie-materiaal (lezen en bekijken):**
> 11. `briefs/website/references/` — screenshots van referentie-sites. **Specifiek**: `ref-a-honeycomb-3d-platform.png` is dé referentie voor de homepage-hero — dat is exact de visuele taal die we willen. Bestudeer die grondig.
> 12. `briefs/website/illustration-batch-1.md` — 12 illustratie-scènes. **Belangrijk: scène 1 (homepage hero) is een UITZONDERING en wordt niet via Midjourney gemaakt** — die bouw je direct als inline interactieve SVG+foreignObject-component (zie hierboven). Scènes 2–12 worden separaat via Midjourney gegenereerd; voor de mock gebruik je daarvoor **placeholder-blokken** met SVG-frames in cobalt en een label-text die beschrijft wat er komt te staan (bv. `<div class="illus-placeholder">[Scène 2: Open source — hex with open top, particles flowing out]</div>`).
>
> **Harde constraints (niet afwijken):**
>
> - **Kleuren**: alleen cobalt (`#21468B`), KNVB-oranje (`#F36C21`), vermiljoen (`#AE1C28`) voor brand-kleuren. Wit (`#FFFFFF`) als achtergrond. Geen andere tinten blauw introduceren. Proportie: ~70% wit, 20% cobalt, 8% oranje, 2% rood.
> - **Typografie**: Figtree (body + headings), IBM Plex Mono (code). Fonts laden via self-hosted of Google Fonts-CDN; in de mock mag een Google Fonts-link prima.
> - **Hexagon altijd pointy-top** (punt boven). Geen flat-top-varianten. Gebruik SVG-clip-paths of inline SVG-hexagons.
> - **Geen "upgrade-druk"**: geen "Try it free"-CTA's, geen "Start your trial", geen pricing-pagina-nags, geen exit-intent-popups, geen urgency-tactics. Primary button zegt altijd *"Install from Nextcloud app store"*, nooit *"Get started"* of *"Sign up"*.
> - **Hexagon voor accenten, niet voor functionele containers.** Buttons / inputs / modals / cards blijven rechthoekig. Hex voor bullets, badges, pagination, avatars, step-indicators, dividers, timeline-kralen, empty-states, loading-spinners.
> - **Tone**: MKB-direct ("je/jij", concreet resultaat, scanbaar). Geen "digitale transformatie", "ketensamenwerking", "toekomstbestendig" — zie `tone-samples.md` voor de verbannen-lijst.
> - **Geen add-to-cart of account-flow**: onze conversie is een klik naar de Nextcloud app store. Geen login, geen signup, geen billing-UI.
> - **Geen JS-animatie-bibliotheek toevoegen**: het platform-diagram (en alle andere animaties op de site) heeft *geen* Framer Motion / GSAP / React Spring / AOS / tailwindcss-animate / Three.js nodig. Pure CSS `transition-colors` + IntersectionObserver is genoeg, dat is ook wat onze referentie Honeycomb gebruikt (zie [`website/honeycomb-teardown.md`](./website/honeycomb-teardown.md)). Voeg geen anim-library toe tenzij expliciet gevraagd.
> - **Bilingual NL/EN**: de mock hoeft maar één taal te tonen, begin met NL. Structuur moet zo zijn dat `/nl/` en `/en/` routes gemakkelijk later kunnen landen (geen hardcoded texts in HTML voor belangrijke content-slots, of wel hardcoded maar met duidelijke `data-i18n`-markers).
>
> **Homepage-structuur** (in deze volgorde, zie `briefs/website/visual-motifs.md §Sectie 1-7`):
>
> 1. **Hero** — **interactieve SVG platform-overview** (Honeycomb-stijl, zie `briefs/website/references/ref-a-honeycomb-3d-platform.png` + `visual-motifs.md §Implementatie`). **Géén rasterized image — bouw hem direct als inline SVG met `<foreignObject>`-HTML-pills zodat hij accessible, editeerbaar, i18n-ready en interactief is.** 6 hex-prisms voor categorieën (Data Foundation / Integration / Documents / Case & Process / Insights / Design), elk met pill-labels voor de apps erin. Externe rechthoeken links ("Je bestaande systemen": Nextcloud, BAG, BRK, PDOK) en rechts ("Integraties": Nextcloud app store, gov-portals, email). Dashed data-flow-paths tussen elementen. Pills zijn `<a>` met `cursor: pointer` + CSS `transition-colors` bij hover. Headline links van het beeld: *"Een ecosysteem van Nextcloud-apps voor MKB en overheid"*, primaire CTA *"Browse our apps"* → `/apps`, secundaire CTA *"Solve a problem"* → `/solutions`.
> 2. **Waarde-teasers** — horizontale honeycomb-row van 4 hex-cards: "Open source" / "Eigen Nextcloud" / "Geen vendor lock-in" / "NL Design"
> 3. **Apps-grid** — offset honeycomb van 11 core apps; elke hex toont icoon + naam op hover/tap-overlay; taglines uit `app-taglines.md`
> 4. **Solutions-teasers** — 3–5 solution-cards met hex-stack-diagram-visual showing de app-stack per solution
> 5. **Stats-strip** — hex-gekaderde getallen: "11 apps", "100+ gemeenten", "install in <2 min", GitHub-sterren-count
> 6. **Support-teaser** — quiet textueel, één zin + link naar `/support` (bewust niet uitgebreid; upgrade-druk vermijden)
> 7. **Footer** — 4–5 kolommen, subtiele hex-pattern-achtergrond op 5–8% opacity
>
> **Hoofdnavigatie** (header, sticky):
>
> - Apps | Solutions | Support | About | Docs (extern, → docs.conduction.nl) | GitHub (extern)
> - Rechts: taalwisselaar NL/EN
> - Geen login-knop, geen "Start for free"-knop
>
> **Footer**:
>
> - Services (pagina, niet in hoofdnav) — tarievenkaart
> - Contact
> - Privacy / Legal
> - Social: GitHub, LinkedIn
> - Taalwisselaar (2e plek)
> - Copyright + open-source-statement
>
> **Output requirements**:
>
> - Eén `index.html` met alle secties
> - Eén `styles.css` met CSS custom properties gelezen uit `brand/tokens.json`
> - SVG-hexagon-primitieven inline of als losse `hex-*.svg`
> - Illustratie-plekken als placeholder-divs met beschrijvende label
> - Responsive breakpoints: 375 / 768 / 1440 (mobile / tablet / desktop)
> - Lighthouse-target: 90+ op Performance / Accessibility / Best Practices / SEO
> - Geen externe dependencies in de mock (geen Tailwind, geen React, geen build-tooling)
>
> **Wat ik van je terug wil**:
>
> 1. Bevestig dat je de documenten hebt gelezen met een korte samenvatting (≤ 300 woorden) van de kern-principes die je gaat toepassen — zodat ik kan checken of je niks gemist hebt
> 2. Dan je eerste mock-versie van de homepage
> 3. Lijst van design-beslissingen die je hebt gemaakt die nog niet in de briefs stonden (spacing-scale, radii, shadows, motion — scope B dingen die nog niet vast waren) — zodat we die kunnen expliciteren in latere iteraties
>
> **Iteratie-model**: ik review per sectie. Als sectie 1 (hero) goed is, ga door naar 2 (values). Als iets niet klopt, rework die sectie. Niet alles tegelijk willen oplossen.
>
> Geen haast. Neem de tijd om de documenten grondig te lezen voordat je begint. Vraag om opheldering bij twijfel.

---

## Volgorde van pagina-types

Na de homepage, in deze volgorde (per sessie één nieuwe pagina):

1. **Homepage** — eerste hele pagina, meest iteratie-intensief
2. **App-detail** (bv. OpenCatalogi) — template voor alle 11 app-pagina's
3. **Apps-catalogus** — het filter-en-grid-patroon
4. **Solution-landing** (WOO-compliance — volledige content in `briefs/website/solution-woo.md`)
5. **Solutions-catalogus**
6. **Support-pagina** — tier-tabel + pricing
7. **Services-pagina** — tarievenkaart
8. **About**
9. **Contact**
10. **404**

Elke volgende pagina hergebruikt de CSS van de vorige — er wordt dus een **component-library** opgebouwd binnen dezelfde `styles.css`.

## Wat te verwachten per mock

Claude Design zal naar alle waarschijnlijkheid op scope-B-tokens (spacing, radii, shadows, motion, breakpoints) impliciete keuzes maken omdat die niet vastliggen in scope A. Dat is prima — die keuzes expliciteren we achteraf door te vragen: *"Welke radii gebruik je? Welke shadows? Welke spacing-scale?"* en die antwoorden codificeren we dan alsnog in `brand/tokens.json` als tokens scope B.

De eerste mock zal dus niet perfect zijn. Dat is verwacht. Iteratie 1 is altijd ruw; iteratie 2–3 is waar de pagina strak wordt.

## Wat Claude Design NIET kan

- **Midjourney-illustraties genereren** — die komen uit `illustration-batch-1.md` via Midjourney zelf; mock gebruikt placeholder-divs
- **Echte foto's maken** — we gebruiken geen foto's, alleen illustraties en hex-graphics; niet aan te vragen
- **Externe API-integratie** — de mock is statisch; geen live Nextcloud-app-store-fetching
- **Bilingual toggle echt werkend** — bilingual wordt pas in Docusaurus-implementatie echt geregeld; in de mock één taal is genoeg

## Post-mock → naar Docusaurus

Als alle pagina-mocks staan en goedgekeurd zijn:

1. **Docusaurus 3.x project opzetten** (separate PR)
2. **Custom thema** dat de mock-CSS hergebruikt; tokens via CSS custom properties
3. **Content in markdown** + frontmatter per app en solution
4. **i18n** via Docusaurus-ingebouwde bilingual support
5. **Deploy** naar GitHub Pages (bestaande gh-pages flow uitbreiden)

Dat is een apart traject. De handoff hier is alleen voor de design-fase.

---

## Troubleshooting

**Als Claude Design de documenten niet lijkt te begrijpen:**
- Paste de relevante sectie direct in het gesprek in plaats van alleen het pad
- Begin kleiner: één sectie van de homepage tegelijk in plaats van de hele pagina

**Als de mock er te generiek uitziet:**
- Benadruk opnieuw: **no stock-feel, no Corporate Memphis, no generic SaaS**. Check tegen de referentie-screenshots in `briefs/website/references/`.
- Vraag expliciet: *"Welk aspect van onze brand is in deze mock aantoonbaar? Als ik er een stoplicht tegenaan houd, is het onmiskenbaar Conduction en niet Rabobank / Odoo / willekeurige SaaS?"*

**Als hexagons niet consistent worden toegepast:**
- Refereer terug aan `visual-motifs.md §Hexagon-catalogus` met de lijst van 14 UI-toepassingen
- Vraag: *"Welke van deze 14 hexagon-toepassingen heb je gebruikt in deze mock? Waar heb je ze bewust overgeslagen en waarom?"*

**Als de tone te formeel is:**
- Paste de `tone-samples.md`-rewrite-recepten als concrete voorbeelden
- Vraag: *"Vergelijk je hero-copy met register A (overheid-formeel) en register C (user-story). Zit het dichter bij C?"*
