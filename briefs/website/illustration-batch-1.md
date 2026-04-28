# Illustratie batch 1 — MVP (10–12 stuks, richting A2, Midjourney)

Definitieve illustratie-keuze: **richting A2** (flat-isometric hex-prism, Honeycomb-stijl). Zie [`visual-motifs.md §Gekozen`](./visual-motifs.md#gekozen-richting-a2--flat-isometric-hex-prism-overall) voor de rationale.

Per illustratie hieronder: **scène-naam**, **waar het wordt geplaatst**, **kant-en-klaar Midjourney-prompt**, en **post-productie-notities**.

## Master-prompt — A2-style (basis voor alle prompts)

Copy-paste deze als style-suffix achter elke scène-specifieke prompt:

```
flat-isometric illustration, hexagonal prisms extruded into 3D viewed from ~30 degree isometric angle, clean flat color fills only, no gradients no lighting no photorealistic 3D, pastel category-color coding: cobalt blue #21468B dominant, KNVB orange #F36C21 accent (max 10% of surface), soft pastel blues purples yellows for differentiation, white background, subtle 2D drop shadows for depth only, thin connecting lines where data flow needs showing, pointy-top hexagons, clean unpretentious Dutch-design feel, style reference honeycomb.io platform overview, no human figures no faces no characters, no text labels unless specified --style raw
```

Voor scènes waar je labels nodig hebt, voeg na de prompt toe:
- `--ar 16:9` voor hero-formaten (16:9 landscape)
- `--ar 4:3` voor breedformaten (solutions, About)
- `--ar 1:1` voor kaart/badge-formaten
- `--ar 3:2` voor semi-landscape

---

## Scène 1: Homepage hero — Platform overview

> **⚠ UITZONDERING: scène 1 wordt niet primair via Midjourney gerealiseerd.**
>
> Reverse-engineering van honeycomb.io (zie [`visual-motifs.md`](./visual-motifs.md#implementatie--bevestigd-via-reverse-engineering-van-honeycombio-2026-04-23)) heeft bevestigd dat hun platform-diagram een **pure SVG met `foreignObject`-HTML-pills** is — geen rasterized image. Dat willen wij ook, omdat het: accessible is, crisp op elke schaal, tekst-editeerbaar zonder design-tool, interactief zonder JS-library, SEO-friendly, en i18n-ready.
>
> **Workflow:**
> 1. Midjourney levert een **visuele referentie** (rasterized) voor hoek, hex-placement, palet — niet een eindproduct
> 2. Claude Design (of een illustrator) **traced/bouwt** de compositie als SVG, inclusief de hex-prism-paden (3 paden per prisma voor top/links/rechts-vlak)
> 3. HTML-pills komen in `<foreignObject>` binnen de SVG
> 4. CSS custom properties voor categorie-kleuren
> 5. `<a>`-pills linken naar app-detail-pagina's; dashed lines als `<path>` met `stroke-dasharray`
>
> Gebruik onderstaande Midjourney-prompt dus alleen om een *referentiebeeld* te genereren waar de SVG op gebaseerd wordt — niet als eindproduct. De screenshot van honeycomb.io in [`references/ref-a-honeycomb-3d-platform.png`](./references/ref-a-honeycomb-3d-platform.png) is eigenlijk al voldoende referentie; Midjourney is optioneel voor deze scène.

**Waar:** `/` hero-sectie (boven de fold, centraal)
**Formaat in SVG:** viewBox `0 0 1290 780` (dezelfde ratio als Honeycomb), responsive via container
**Prioriteit:** Hoogste — dit is THE visual van de hele site

**Optionele Midjourney-referentieprompt (niet voor eindproduct, alleen voor inspiratie):**

```
platform overview diagram, 6 hexagonal prisms arranged in central cluster with one dominant green hexagon in middle, labeled feature-pill badges floating near each hex showing app names, external rectangular boxes on left and right connected by thin dashed data-flow lines, left box labeled "Your systems" with small logo placeholders for Nextcloud BAG BRK PDOK, right box labeled "Integrations" with placeholders for app store and gov portals, [MASTER PROMPT]
```

**SVG-bouwinstructies voor Claude Design / illustrator (definitief, 6-component-card-architectuur rondom Nextcloud-kernel):**

**Strategische narrative**: ConNext is Conduction's propositie die Nextcloud doorontwikkelt van *office suite* naar *workspace*. De 6 component-cards rondom de Nextcloud-kernel laten zien wat die uitbreiding inhoudt.

**Centrum — Nextcloud kernel (één grote hex-prism, cobalt + Nextcloud-blauw gradient):**
- Pills binnen Nextcloud-kernel: `Files` · `Mail` · `Calendar` · `Contacts` · `Talk` · `Office` · `Apps & SSO`
- Visuele behandeling: iets groter dan de component-cards eromheen; gebruikt Nextcloud-blauw `#0082C9` als secundaire tint (top-face) bovenop cobalt (left/right faces)
- Label onder de hex: "Nextcloud" (in Nextcloud-blauw)

**Zes component-cards rondom de kernel** (in Honeycomb-stijl arrangement, elk een hex-prism met pastel-tint en pill-labels):

1. **Technical Core** (cobalt-diep / donkerblauw) — *Conduction's fundering-laag (5 fundamentele capabilities)*
   - Pills: `OpenRegister` (data) · `OpenConnector` (integratie) · `DocuDesk` (documenten) · `NLDesign Theme` (theming) · `MyDash` (dashboards)

2. **Workplace App** (warm coral / rood-oranje) — *user-facing apps voor concrete use cases (9 pills)*
   - Pills: `OpenCatalogi` · `PipelinQ` · `Procest` · `ZaakAfhandelApp` · `DeciDesk` · `ShillinQ` · `LarpingApp` · `OpenWoo` · `SoftwareCatalog`
   - Bij verdere groei van Workplace Apps boven ~10 pills: overweeg split in twee thematische hexen (records vs process) of *"View all → /apps"*-pill aan einde lijst

3. **AI** (paars / lavendel) — *AI-capabilities cross-cutting over de stack*
   - Pills: `Automation` · `Agents` · `Intelligence`

4. **Integrated Apps** (geel / oker) — *externe open-source apps in jouw Nextcloud*
   - Pills: `OpenTalk` · `Matrix` · `n8n` · `OpenProject` · `XWiki` · `GitLab` · `Mattermost`

5. **App Builder** (groen / mint) — *vitaal ecosystem-onderdeel: een UI waarmee klanten zelf (mini) Nextcloud-apps bouwen of bestaande ConNext-apps customizen, gebruikmakend van de Technical Core* — **`Coming soon`-badge** zichtbaar
   - Pills: `Build your own` · `Customize ConNext apps` · `No code, just configure`
   - **Strategische narrative**: *"The client is always right — and now they have the tools to make it true."* — empowerment-pitch die op de App-Builder-detail-pagina prominent terugkomt
   - Visueel: zelfde stijl als de andere component-cards maar met een kleine, opvallende `Coming soon`-pill in oranje (KNVB) of een speciale badge-shape rechts-bovenin de hex

6. **Admin Tools** (grijs / lichtblauw, gedempt) — *utilities voor admins, geen primair product*
   - Pills: `App-versions` · `Crontab`
   - Visueel: iets kleiner of met lagere opacity dan de andere component-cards om "ondersteunend, niet voorgrond"-status duidelijk te maken

**Side-box — Links: "Your data sources" / "Je bestaande omgeving":**
- BAG · BRK · PDOK · BRP · KvK · DSO (overheid bron-iconen)
- Plus: existing Nextcloud-data (Files, Contacts) als ingang
- Geen rechts-side-box meer — externe productivity-apps (OpenProject, XWiki, etc.) zitten nu in de **Integrated Apps** component-card

**Verbindingen / data-flow:**
- Stippeltjes-flow-lijnen (`stroke-dasharray="2.41 3.85"`, statisch zoals Honeycomb) van **Side-box** → **Nextcloud kernel** (data-input)
- Stippeltjes van **Nextcloud kernel** → **alle component-cards** rondom (kernel voedt componenten)
- Subtiele cross-component-lijntjes tussen sterk-samenwerkende paren (bv. **Workplace App** ↔ **AI**, **Technical Core** ↔ **Integrated Apps**)
- Geen flow-lijn richting **Admin Tools** of vanaf **App Builder** — die zijn voorlopig non-data-flow

**Per-element styling:**
- Hex-prism = 3 `<path>`'s (top, links, rechts) met drie tinten van dezelfde pastel-familie voor isometrische diepte
- Default opacity ~70% op alle hex-paden, `group-hover:opacity-100` voor spotlight-effect (zie [`honeycomb-teardown.md §6.5`](./honeycomb-teardown.md))
- Pills als `<a href>` binnen `<foreignObject>` — clickable, focus-bare, screen-reader-leesbaar
- CSS `transition-colors duration-150` op pill-hover
- App-Builder `Coming soon`-badge: standalone `<span class="badge badge-coming-soon">` in oranje, niet-clickable, `aria-label="App Builder is in active development; subscribe to the newsletter for launch notice"`

**Wordmark + lockup boven de diagram:**
- ConNext-wordmark in cobalt+Nextcloud-blauw, prominent
- "by Conduction" subtitel onder de wordmark, klein en in cobalt
- Conduction-hexagon-avatar als kleine icoon naast de "by Conduction"-tekst, links

## Scène 2: Waarde-teaser — "Open source"

**Waar:** Homepage sectie 2, blok 1 van 4
**Formaat:** 1:1, 800×800px

**Prompt:**

```
single hexagonal prism with its top face open, lines of small stacked hexagons flowing up and out of the opening like rising particles, symbolizing openness and outflow of content, cobalt blue prism, orange accent on the rising particles, [MASTER PROMPT] --ar 1:1
```

**Post-productie:**
- Label onder de illustratie in Figma: "Open source"

## Scène 3: Waarde-teaser — "Eigen Nextcloud"

**Waar:** Homepage sectie 2, blok 2 van 4
**Formaat:** 1:1, 800×800px

**Prompt:**

```
one large outer hexagonal prism containing 4 smaller hexagonal prisms nested inside, representing containment or self-hosting, outer hex in neutral cobalt outline, inner hexes in filled cobalt with one orange accent, clean composition showing apps inside a container, [MASTER PROMPT] --ar 1:1
```

**Post-productie:**
- Label: "Eigen Nextcloud"

## Scène 4: Waarde-teaser — "Geen vendor lock-in"

**Waar:** Homepage sectie 2, blok 3 van 4
**Formaat:** 1:1, 800×800px

**Prompt:**

```
single hexagonal prism standing free on an isometric plane with visible open space around it, no cables or connections attached, contrast with faded background showing broken or dissolved chain-links, cobalt prism dominant, one orange accent on the chains being broken, symbolizing freedom and no lock-in, [MASTER PROMPT] --ar 1:1
```

**Post-productie:**
- Label: "Geen vendor lock-in"

## Scène 5: Waarde-teaser — "NL Design"

**Waar:** Homepage sectie 2, blok 4 van 4
**Formaat:** 1:1, 800×800px

**Prompt:**

```
hexagonal prism with the Dutch flag colors as internal layered strips (cobalt blue base layer, white middle layer, vermillion red top layer, plus orange accent stripe representing NL heritage), clean isometric rendering, minimal and elegant not kitsch, [MASTER PROMPT] --ar 1:1
```

**Post-productie:**
- Label: "NL Design"
- Zorg dat het meer abstract-layered-is dan letterlijk-vlag — kitsch vermijden

## Scène 6: Solution — WOO-compliance

**Waar:** `/solutions/woo-compliance` hero + homepage solution-teaser
**Formaat:** 4:3, 1600×1200px

**Prompt:**

```
on the left side a scattered fragmented field of small ungrouped hexagonal outlines representing silo'd information, on the right side those same hexagons consolidated into a clean organized hex-cluster with one prominent orange-accented hex floating above representing the Woo-index harvester, thin dashed data-flow lines showing movement from left to right, visual metaphor of fragmentation-to-order, [MASTER PROMPT] --ar 4:3
```

**Post-productie:**
- Labels in Figma: "Versnipperde bronnen" (links) → "Gepubliceerd en vindbaar" (rechts)
- Orange hex bovenaan krijgt klein label "Woo-index"

## Scène 7: Solution — Organisatieregister

**Waar:** `/solutions/organisatieregister` hero + homepage solution-teaser
**Formaat:** 4:3, 1600×1200px

**Prompt:**

```
central large hexagonal prism in cobalt labeled conceptually as core registry, surrounded by smaller satellite hexes in varied pastel colors connected by thin dashed lines, each satellite representing a different data-domain, one satellite highlighted in orange, isometric perspective, clean composition emphasizing the center-periphery relationship, [MASTER PROMPT] --ar 4:3
```

**Post-productie:**
- Central label: "Organisatieregister"
- Satellite labels: "Personen", "Afdelingen", "Rollen", "Processen", "Documenten"

## Scène 8: Solution — Zaakafhandeling

**Waar:** `/solutions/zaakafhandeling` hero + homepage solution-teaser
**Formaat:** 4:3, 1600×1200px

**Prompt:**

```
horizontal flow of 4 to 5 hexagonal prisms arranged in a path from left to right, each hex representing a case-state, connected by thick arrow-like lines, first hex in neutral outline, middle hexes filled cobalt, final hex filled cobalt with orange accent, symbolizing case progression through states, isometric view, [MASTER PROMPT] --ar 4:3
```

**Post-productie:**
- State-labels onder elke hex: "Ingediend", "In behandeling", "Advies", "Besluit", "Afgehandeld"

## Scène 9: About — "Onze plek in het NL-gov-ecosystem"

**Waar:** `/about` hero
**Formaat:** 4:3, 1600×1200px

**Prompt:**

```
abstract Dutch ecosystem composition, one prominent cobalt hexagonal prism in the center representing Conduction, surrounded by a constellation of other hex-prisms in various pastel colors representing NL-gov partners and standards (Common Ground, NL Design System, Nextcloud ecosystem), loose organic arrangement not rigid grid, thin connecting lines between related hexes, isometric perspective, [MASTER PROMPT] --ar 4:3
```

**Post-productie:**
- Central label: "Conduction"
- Satellite labels: "Common Ground", "NL Design System", "Nextcloud", "gemeenten", "VNG", "maatschappelijk domein" (one per satellite)

## Scène 10: 404 — Lost in the grid

**Waar:** `/404` hero
**Formaat:** 16:9, 1600×900px

**Prompt:**

```
a large connected cluster of hexagonal prisms arranged on the right side of the frame, and on the left side one single isolated outline-only hexagon drifting away from the cluster with a thin dotted trail back to it, sense of something lost but findable, cobalt prisms in the cluster, the isolated hex is light outline in the same cobalt, orange accent on one prism in the cluster as a "you are looking for me" signal, isometric view, [MASTER PROMPT] --ar 16:9
```

**Post-productie:**
- H1 tekst: "Lost in the grid"
- Lead: "Deze pagina zweeft ergens zonder connectie. Laten we je terug naar huis sturen."

## Scène 11: Empty state — "Niks gevonden"

**Waar:** Apps-catalogus filter met geen resultaten, zoekpagina zonder hits
**Formaat:** 1:1, 600×600px

**Prompt:**

```
single empty hexagonal prism outline with a subtle question-mark shape inside made of a few tiny dotted hexagons, minimalist composition lots of negative space, cobalt outline only no fill, one orange accent dot as the question mark, isometric view, [MASTER PROMPT] --ar 1:1
```

**Post-productie:**
- Tekst onder: "Niets gevonden. Pas je filter aan of [vraag een nieuwe app aan](GitHub-link)."

## Scène 12: Support-teaser — Standard & Premium

**Waar:** `/support` hero + homepage support-teaser
**Formaat:** 3:2, 1500×1000px

**Prompt:**

```
two hexagonal prisms side by side on an isometric plane, left prism smaller and shorter in muted cobalt outline labeled conceptually as "standard tier", right prism larger and taller in filled cobalt with a small orange hex-accent floating above it labeled conceptually as "premium tier", visual hierarchy clearly showing upgrade path without aggression, clean composition with clear separation between them, [MASTER PROMPT] --ar 3:2
```

**Post-productie:**
- Left label: "Support Standard — helpdesk + monthly telemetry"
- Right label: "Support Premium — helpdesk + real-time alerts"

---

## Productie-workflow

1. **Genereer alle 12 in één Midjourney-sessie** met deze prompts. Maak van elke scène 4 variants (`--chaos 5` voor milde variatie, of gewoon de default 4-grid).
2. **Kies per scène 1 definitieve variant** via een eerste Conduction-team-review (15 min).
3. **Upscale** de gekozen variants naar `--zoom 1` of hoger voor print-kwaliteit.
4. **Voer post-productie** uit in Figma/Illustrator:
   - Labels vervangen door onze echte tekst (Figtree lettertype)
   - Categorie-kleuren aanpassen als Midjourney niet exact matcht
   - Eventueel orange-accent aanpassen naar #F36C21 exact
   - Cobalt aanpassen naar #21468B exact
5. **Export** naar SVG + PNG (2× retina) en lever in `.github/brand/assets/illustrations/` zodat alle Conduction-oppervlakken ze kunnen gebruiken.
6. **Versie-controle**: commit de source-prompts hier in dit document zodat we bij stijlfouten terug kunnen naar de bron.

## Checklist voor review

Per illustratie afgetoetst voor goedkeuring:

- [ ] Hexagons zijn pointy-top (punt boven)
- [ ] Flat-isometric; geen gradients, geen lighting, geen photorealistisch 3D
- [ ] Cobalt #21468B is dominant (>60% van gekleurd oppervlak)
- [ ] KNVB oranje #F36C21 is max 10%, accent-only
- [ ] Geen mensen, gezichten, karakters
- [ ] Witte achtergrond
- [ ] Subtiele 2D drop-shadow voor diepte — niet meer
- [ ] Stijl consistent over alle 12 scènes (niet 12 verschillende "looks")
- [ ] Labels zijn verwijderd of leesbaar in Figtree-adjacent sans-serif

## Open punten voor post-productie

- **Categorie-kleuren** precies vaststellen voor post: welke pastel-tint-familie, hoeveel contrast-spread? Voorstel: cobalt-kern, aangevuld met pastel-oranje (#F4B79B), pastel-geel (#F4DC8B), pastel-groen (#8BC4A4), pastel-paars (#B19CD4), pastel-roze (#E8A5B2). Deze nog te bevestigen.
- **Figma-library** aanleggen waar post-processed illustraties als componenten beschikbaar zijn voor hergebruik over pagina's.
- **Accessibility**: elke illustratie krijgt een `alt`-tekst die de boodschap beschrijft — niet de visuele compositie. Voorbeeld voor Scène 1: `alt="Overzicht van het Conduction ecosystem: zes app-categorieën die data uit je bestaande systemen ontvangen en naar externe integraties doorgeven"`.
