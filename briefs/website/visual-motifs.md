# Visuele motieven — hexagon-systeem, per-sectie-treatments, illustratie-stijl

Dit document beschrijft drie visuele beslissingen die de identiteit van de website fundamenteel bepalen. Ze horen bij elkaar omdat ze samen het **gevoel** van de site bepalen — meer dan kleur of typografie alleen doen.

1. **Hexagon als systematisch motief** — niet alleen de logo-wrapper, maar een terugkerend vorm-element over de hele UI (bulletjes, paginering, statussen, dividers, badges, …). Company-wide, dus ook relevant voor DESIGN.md.
2. **Per-sectie-treatments** — elke sectie van de site verdient bewuste gedachte over hoe we er iets bijzonders van kunnen maken. Niet alleen "hero + tekst + screenshot".
3. **Illustratie-stijl** — vector-line-figuren zoals op de huidige site, met een bepaalde gekende stijl. We kiezen hier een specifieke named style zodat een designer of AI reproduceerbare output levert.

---

## 1. Hexagon als systematisch motief

De zeshoek is Conduction's merk-vorm. Op de huidige stijl komt ze alleen voor rond het logo. Op de nieuwe site maken we er een **systeem** van — een herhalende vorm die op veel plekken in de UI terugkomt, zodat elke pagina zonder twijfel als "Conduction" herkend wordt.

### Regel: hexagon voor accenten, niet voor functionele containers

De zeshoek gaat op plekken waar een **vorm** betekenis heeft (accent, indicator, icoon, badge, markering). Niet op plekken waar een **container** een functie heeft (input, knop, modal, content-card). Functionele elementen blijven rechthoekig omdat dat beter klikt, tikt, leest en invult.

### Toepassingen — een catalogus

Onderstaande UI-elementen krijgen een hexagonale behandeling. Per element: welke vorm, hoe rendert het, wanneer inzetten.

| Element | Hexagon-behandeling | Wanneer |
|---|---|---|
| **List-bullets** | Kleine filled hex (6–8px) i.p.v. `•` bullet | In alle `<ul>`'s in body-tekst; CSS via pseudo-element |
| **Pagination** | Numbered hexagons — actieve pagina = gevuld cobalt; rest = outline | Catalogus-pagina's, blog-lijsten, zoekresultaten |
| **Step-indicators** | Hex-kralen op een horizontale lijn, current step gevuld | Multi-step-flows (onboarding, checkout-achtige flows — al hebben we die nauwelijks) |
| **Progress-bars** | Segmented progress als hex-reeks, gevulde hex = voltooid | Long-form-forms, onboarding-flows |
| **Status-badges** | Hex-pill i.p.v. rechthoekige pill voor app-status (stable / beta / experimental) | App-catalogus, app-detail-hero |
| **Avatars** | Hex-clipped foto (mask) met 2px cobalt-outline | About-pagina, team-sectie, testimonial-quotes |
| **App-logo's** | Hex-wrapper (al bestaand) | Alle app-iconografie |
| **Category-tags** | Hex-wrapped label met kleine hex-bullet ervoor | Solution-categorieën, app-filter-chips |
| **Ratings / scales** | Hexagons i.p.v. sterren (5 gevulde hexen = top rating) | Als we ooit ratings tonen — zie open vraag |
| **Section-dividers** | Horizontale dunne lijn onderbroken door één hex midden | Tussen homepage-secties, lange solution-pagina's |
| **Timeline-beads** | Hex-kralen op verticale of horizontale as | About-pagina's "Onze geschiedenis"-sectie, roadmap |
| **Empty-states** | Outline-hex met icoon erin — "niks gevonden"-illustraties | Lege catalogus-resultaten, 404-pagina |
| **Loading-spinner** | Pulserende hex of draaiende hex-constellatie | Overal waar async-laden gebeurt (apps-filter, zoek) |
| **Bullet-chars in pros/cons-lijsten** | Kleine filled hex met cobalt/oranje kleur naar sentiment | Do's/don'ts-blokken |
| **Section-headers** | Kleine hex-accent voor of achter de H2 | Optioneel, voor visueel ritme op lange pagina's |

### Wat **géén** hexagon krijgt

Functionele UI die rechthoekig hoort te zijn:

- Tekst-inputs, textareas, selects, checkboxes, radio-buttons — allemaal rechthoekig
- Buttons (primary/secondary/tertiary) — rechthoekig met subtiele radius
- Modals, dialogs, drawers — rechthoekig
- Content-cards (app-cards, solution-cards) — rechthoekig; het is de content die hex-accent krijgt (icoon, badge), niet de kaart
- Tables — rechthoekig
- Code-blocks — rechthoekig

De regel: als iemand *iets doet* met het element (typen, klikken, lezen), is het rechthoekig. Als het element *iets aanduidt* (status, volgorde, categorie), mag het hex zijn.

### Implementatie-niveau

**Technisch:**

- **Pure CSS hex** via `clip-path: polygon(25% 0%, 75% 0%, 100% 50%, 75% 100%, 25% 100%, 0% 50%)` voor rechte hex, of `clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)` voor gedraaide hex
- **SVG hex** als icoon-primitief; bij gebruik als bullet inline via `<svg>` of als achtergrond-`url()`
- **Design-token** `shape.hexagon` in scope-B tokens met 2 varianten: `pointy-top` en `flat-top` (verschillende oriëntaties voor verschillende toepassingen)
- **Accessibility:** hex-vormen zijn puur decoratief; screen-readers negeren ze via `aria-hidden="true"`. Functie-dragend hex-icoon krijgt `aria-label`.

**Oriëntatie-keuze:**

- **Flat-top** (platte zijde boven) — standaard voor het Conduction-logo (bestaande avatar) en voor alle logo-wrappers
- **Pointy-top** (punt boven) — voor UI-elementen (bullets, badges) omdat die visueel iets vriendelijker en opvallender zijn

Één project, beide oriëntaties. Dit is geen probleem zolang het bewust is.

---

## 2. Per-sectie-treatments — iteraties en aanbevelingen

Elke sectie van de website verdient een eigen doordenking — niet *"hero + tekst + screenshot"* voor alles. Per sectie zetten we 2–4 alternatieven naast elkaar en recommenden er één, met rationale.

### Homepage

#### Sectie 1: Hero

**Opties:**

- **A. Screenshot van één app** — conservatief, gebruiksgericht, saai
- **B. Ecosystem-constellatie** — centrale hex ("Conduction") met satellite-hexes (apps) eromheen, verbindingslijntjes, rustige animatie
- **C. Gelaagde hex-grid** — hexagonaal patroon op achtergrond, morphing of subtiel scrollend parallax
- **D. Eén grote hex met screenshot erin gecropt** — boldere statement maar beperkt tot één app
- **E. Typografie-eerst** — grote headline, geen beeld-hero, slechts hex-accenten

**Aanbevolen: B — Ecosystem-constellatie.**

Waarom: communiceert in één oogopslag de kern-boodschap ("apps die samenwerken in een ecosystem") zonder text. Hex-vorm-herhaling versterkt merk. Animeert rustig (≤ 1 keer per 10s) zodat het niet afleidt. Mobile-fallback: kleinere, statische versie of alleen de centrale hex met app-namen in cirkel eromheen.

Escape-hatch: als B te technisch ogend wordt, terug naar A met hex-frame om de screenshot.

#### Sectie 2: Waarde-teasers (4 blokken: "Open source" / "Eigen Nextcloud" / "Geen vendor lock-in" / "NL Design")

**Opties:**

- **A. 4 cards naast elkaar** — baseline, kaal
- **B. Honeycomb-row** — 4 hexagons die elkaar raken, icoon + titel + 1-regel-uitleg per hex
- **C. Staggered honeycomb** — 2 hexes boven, 2 onder, offset zoals een echte honeycomb
- **D. Centrale hex ("Conduction") omringd door 4 waarde-hexes** — visualiseert dat deze 4 waardes definieerden wie we zijn

**Aanbevolen: B — Horizontale honeycomb-row.**

Waarom: 4 raakelkaar-hexagons zijn direct herkenbaar als "honeycomb" (ecosystem-metafoor); werkt horizontaal op desktop; stackt netjes verticaal op mobile (wordt dan verticale kolom van 4 hexes). C is elegant maar vraagt meer verticale ruimte; D is te meta.

#### Sectie 3: Apps-grid — het hart van de homepage

Dit is de sectie waar je voorstel voor is gekomen:

- **Offset honeycomb-grid op desktop** — hexagons in een interlocking-patroon (twee rijen waarvan de tweede offset)
- **Elke hex bevat het app-icoon** — centraal, cobalt op wit
- **Hover over de hex**: cross-fade-overlay met app-naam + tagline uit [`app-taglines.md`](./app-taglines.md)
- **Klik**: navigeer naar app-detail

**Implementatie-details:**

- Grid-shape: 4-3-4 (offset) op desktop = 11 apps precies passend; 3-4 rijen op tablet; verticale lijst op mobile
- Mobile-fallback (< 768px): hex-icoon + tagline + "Read more" als verticale lijst, geen hover-trick
- Hover-transition: 200ms ease-out cross-fade
- Touch-friendly: tap/focus triggert dezelfde overlay (accessibility voor touch + keyboard)
- Accessibility: icoon heeft `aria-label` met app-naam; tagline in `aria-describedby`; reduced-motion respecteert = fade met 0ms
- Optional: subtle lift op hover (translateY(-2px) + shadow)

**Micro-interactie-idee:** bij laden *honeycomb builds in* — hexes verschijnen één-voor-één met 50ms stagger (totaal ~600ms). Geen blocking, alleen ritme.

#### Sectie 4: Solutions-teasers

**Opties:**

- **A. 3–4 cards horizontaal** — baseline
- **B. Hex-vormige solution-cards** — zelfde als apps maar met probleem-iconen (iets algemener)
- **C. Stack-diagram-teaser per solution** — klein hex-diagram dat de apps-stack achter elke solution toont (bv. WOO = OpenRegister + OpenCatalogi + OpenConnector + DocuDesk als geconnecteerde hexes)
- **D. "Probleem → Oplossing"-visual** — pain-point links, hex-pijl, app-stack rechts

**Aanbevolen: C — Stack-diagram-teaser.**

Waarom: communiceert op elke solution-kaart direct onze **onderscheidende boodschap** ("solutions = compositie van apps"). Dit is lezen-bestendig — iedere kaart toont waarom de solution uit óns ecosystem komt, niet uit een magische blackbox. Vanuit hier is de klik naar de volledige solution-pagina logisch.

Simpeler fallback: als C te druk oogt, kleine hex-iconen met tekst (variant van A met hex-accent).

#### Sectie 5: Stats-strip

**Opties:**

- **A. 4 grote getallen naast elkaar** — baseline
- **B. Hex-gekaderde getallen** — elk getal in een grote decoratieve hex
- **C. Honeycomb-achtergrond-patroon** met getallen daarover
- **D. Count-up-animatie** on scroll-into-view (getallen tellen op van 0)

**Aanbevolen: B + D — Hex-gekaderde getallen met count-up-animatie.**

Waarom: hex-frames verankeren het motief; count-up-animatie geeft leven bij scroll zonder dat het irriteert (gebeurt één keer). Mobile: staat stack; count-up blijft werken.

Respectering reduced-motion: animatie uitgeschakeld voor users die dat instellen.

#### Sectie 6: Support-teaser

**Opties:**

- **A. Standaard CTA-strip met "Explore Support"** — baseline
- **B. Twee hex-cards naast elkaar** — Standard + Premium als previews
- **C. Hex-gradient** — twee opeenvolgende hexes die tiers visualiseren
- **D. Quiet textueel** — één zin, één discreet hex-accent, één link

**Aanbevolen: D — Quiet textueel.**

Waarom: dit is bewust *niet* een sales-moment. Onze toon is "apps zijn gratis, Support is optioneel voor wie het wil". Een grote Support-strip zou die boodschap ondermijnen. Eén zin, subtiele hex-ornament, link naar `/support`. Klaar.

Concrete copy: *"Zelfstandig genoeg? Prima. Meer zekerheid nodig? Onze [Support](./support) zit klaar."*

#### Sectie 7: Footer

**Opties:**

- **A. Standaard 4-kolommen-footer** — baseline
- **B. Hex-pattern achtergrond** — subtiel honeycomb-patroon op 5–8% opacity als achtergrond
- **C. Hex-dividers tussen footer-secties** — kleine hex-ornament tussen kolommen
- **D. "Honeycomb-hive"-footer** — gestileerd honeycomb-element als visuele afsluiting van de pagina

**Aanbevolen: B — Subtiele hex-pattern-achtergrond.**

Waarom: afsluiting als "je zit nog steeds op een Conduction-pagina" zonder op te drukken. Pattern op 5–8% opacity is perceptibel maar niet storend. Mobile: zelfde pattern, desnoods iets groter schaal voor herkenbaarheid.

### App-detail-pagina

- **Hero**: hex-framed app-logo links, screenshot rechts
- **Sticky intra-page-nav**: hex-iconen per sectie (Features / Screenshots / Integraties / Tech / Install)
- **Feature-blokken**: hex-bullets in feature-lijsten
- **"Integreert met"**: visualiseert als mini-constellatie van hex-app-logos (zelfde stijl als homepage-hero maar kleiner)
- **Technical metadata-sidebar**: hex-accenten bij licentie, versie, NLDS-compliance
- **Install-CTA**: rechthoekige button (functioneel) met hex-icoon naast de label-tekst

### Solution-landing

- **Hero**: probleem-titel met kleine hex-ornament links
- **"Stack-diagram"-sectie**: hex-compositie die de apps toont; elke hex = één app; lijnen tonen relaties
- **FAQ**: hex-bullet per vraag-regel
- **App-stack-tabel**: tabel is rechthoekig, maar iedere app-rij krijgt hex-geframed app-icoon

### Support-pagina

- **Hero**: kleine hex-accent
- **Tiers-kolommen**: 2 kolommen (Standard, Premium). Hex-icoon bovenaan elke kolom (Standard = outline-hex; Premium = gevulde hex) — visuele hiërarchie-suggestie
- **Pricing-tabel**: rechthoekig (functioneel), maar elke app-rij heeft hex-app-icoon
- **Paden 1 en 2**: twee honeycomb-blokken naast elkaar, elk met zijn flow

### Services-pagina

- **Tarievenkaart**: rechthoekige tabel (functioneel); elk dienst-type heeft hex-icoon (dev, consultancy, training, cert)
- **Strippenkaart-visual**: stack van hex-kralen die aftellen bij gebruik — speelse visualisatie van "uren worden afgeboekt van je strippenkaart"
- **Training-varianten**: 3 hex-cards (fysiek / online / certificering)

### About

- **Team-sectie**: hex-clipped portretfoto's (eindelijk ons motief op foto's!)
- **Timeline**: hex-kralen op verticale lijn voor milestones
- **Values**: 5 hexes die onze 5 kernwaarden (Trots NL / Innovatief / Handelsgedreven / Penny-wise / Betrouwbaar) tonen

### 404

- Grote outline-hex met vraagteken erin, "lost in the grid" copy
- Zoekveld + links naar Apps / Solutions / Home
- Optioneel: subtiele geanimeerde honeycomb-achtergrond (hexes die rustig pulseren)

---

## 3. Illustratie-stijl — named style te bevestigen

De huidige conduction.nl gebruikt vector-based line-figuren. Welke **named style** precies — moeten we vastleggen zodat de designer (of AI) reproduceerbare resultaten levert. Ik kon via web-fetch de afbeeldingen zelf niet zien (tool ziet alleen HTML-tekst); daarom de kandidaten hieronder — bevestig welke overeenkomt, of beschrijf de stijl zodat we hem kunnen benoemen.

### Kandidaat-stijlen (vector-based line-figures)

| # | Stijl | Beschrijving | Link | Commercieel bruikbaar? |
|---|---|---|---|---|
| 1 | **Open Peeps** | Thick-outline line-art characters, zwart-op-transparant default, aanpasbaar. Gemaakt door Pablo Stanley. Losse lichaamsonderdelen die je kunt combineren. | [openpeeps.com](https://openpeeps.com) | Ja (CC0-licentie — helemaal vrij) |
| 2 | **Humaaans** | Mix-and-match character-illustraties; gedeeltelijk gevuld met vlakken, met dunne outline-accenten. Ook van Pablo Stanley. | [humaaans.com](https://humaaans.com) | Ja (CC BY 4.0) |
| 3 | **Blush** | Collectie scènes van Pablo Stanley + andere kunstenaars. Thick-outline figuren, vaak met warmere kleurvlakken. | [blush.design](https://blush.design) | Ja (gemengd; sommige scenes gratis, sommige paid) |
| 4 | **Storyset Line** | Freepik's line-only variant — complete scenes, geen zwart-vlak, alleen lijnen in één kleur. | [storyset.com](https://storyset.com) | Ja (gratis met attributie, paid voor zonder) |
| 5 | **Drawkit Line** | Line-based illustrations met ronde vormen, iets cleaner dan Blush. | [drawkit.com](https://drawkit.com) | Ja (paid-tier ruim beschikbaar) |
| 6 | **Icons8 Ouch! Lineal** | Massive illustratie-library met line-stijl variant; goede dekking van scenes en characters. | [icons8.com/illustrations/style--lineal](https://icons8.com/illustrations/style--lineal) | Ja (paid of free met attribution) |
| 7 | **Streamline Line** | Enterprise-grade illustratie-library, >30k assets in consistente line-stijl. | [streamlinehq.com](https://streamlinehq.com) | Ja (paid) |

### Mijn aanrader: **Open Peeps** of **Storyset Line**

Beide passen bij vector-based-line-figures + zijn licensing-clean:

- **Open Peeps** als we karakters willen (mensen in verschillende poses — samenwerken, werken achter computer, brainstormen). Thick-outline, zwart default maar recolorable → we kunnen alles in kobalt outlinen met KNVB-oranje accents.
- **Storyset Line** als we complete scènes willen (workflow-visualisaties, abstract concepten, niet alleen mensen). Eén-kleur-line-scenes die we ook kobalt kunnen maken.

**Ideaal:** mix van beide — Open Peeps voor character-moments (About, testimonials, "meekijkend support"), Storyset Line voor concept-illustraties (homepage-waardes, solution-pagina's).

### Alternatief: custom illustratie-stijl (described for reproducibility)

Als we geen gekende library overnemen, maar een eigen stijl willen laten maken door een illustrator of AI, is dit de briefing-tekst die we aan de illustrator/AI geven zodat het consistent wordt:

> *"Vector-based line illustrations of human figures and abstract scenes. Thick uniform outline weight (2–3px at source scale). Rounded, friendly shapes. Minimal facial features (two dots for eyes, simple line for mouth). Limbs proportional but slightly elongated for elegance. Colors: cobalt blue (#21468B) outline with KNVB orange (#F36C21) accents only, on white background. No 3D, no shading, no gradients. Style reference: Open Peeps and Storyset Line hybrid. Composition: one or two figures per illustration, sometimes with geometric props (hexagons, stacked shapes) as environment. Dutch-inflected feel: unpretentious, competent, warm."*

Dit is genoeg voor een AI-tool als Midjourney (met `--style raw`) of voor een freelance-illustrator als briefing. Bewaar deze briefing-tekst als de "master-prompt" voor alle toekomstige illustraties.

### Wat zeker **niet** werkt

- **"Corporate Memphis"** / Alegria-stijl (vlakke character-illustraties met overdreven lange ledematen, felle pastels) — te corporate-bland, te vaak gedaan, matcht onze trotse-Nederlandse-identiteit niet
- **Isometrische illustraties** — te "enterprise-saaS", niet warm genoeg
- **3D-render-stijl** (Lottiefiles-type) — botst met onze flat-plus-hexagon-richting
- **Karikatuur of cartoon** — te informeel voor MKB-beslissers
- **Foto-realistische stockillustraties** — past niet bij line-art-stijl

### Open vraag voor je

1. Welke stijl staat er nu op conduction.nl? Is het één van de 7 genoemde kandidaten, of iets anders?
2. Als het iets anders is — kun je de stijl beschrijven of een voorbeeld-URL delen zodat ik hem kan benoemen?
3. Willen we meegaan met de huidige stijl, of is dit het moment om te vernieuwen?

Zodra deze vraag beantwoord is, documenteer ik de definitieve named-style in BRAND.md (company-wide) zodat elke toekomstige bron (website, drukwerk, apps, presentaties) consistent is.

---

## Open punten

- **Illustratie-stijl bevestigen** (zie hierboven)
- **Hex-animation-budget** — hoe veel animatie is gepast? Voor nu: één micro-interactie per sectie (entrance-stagger, hover, count-up). Reduced-motion altijd gehonoreerd. Verdere bijstelling na eerste mock.
- **Hex-tokens in tokens.json** (scope B) — voeg `shape.hexagon.pointy-top` en `shape.hexagon.flat-top` toe als reusable clip-paths, plus `spacing.hex-grid-gap` voor honeycomb-layouts
- **Honeycomb-layout-breakpoints** — op welke viewport stapt honeycomb over naar vertical stack? Voorstel: 768px. Valideren in de eerste mock.
- **Hex-bullet in body-tekst leesbaarheid** — potentieel visueel zwaar voor lange lijsten; bewaak met testen of het niet irriteert bij > 5 items. Anders: hex alleen voor bullet-lijsten tot 4 items, traditionele `•` voor langere.
