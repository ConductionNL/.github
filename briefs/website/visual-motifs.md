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

**Oriëntatie: altijd pointy-top.**

De Conduction-zeshoek heeft altijd de **punt naar boven**. Geen uitzonderingen, geen flat-top-varianten. Reden: één consistente oriëntatie maakt de vorm onmiddellijk herkenbaar als "Conduction" op elk oppervlak. Het bestaande logo is pointy-top; de bestaande portret-frames zijn pointy-top; dus alles blijft pointy-top.

Bij honeycomb-patronen (meerdere hexagons aaneengesloten) stapelen pointy-top-hexes in offset rijen horizontaal — dat werkt qua layout prima.

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

## 3. Illustratie-stijl — expliciete breuk met het huidige, fresh direction

### Wat de huidige stijl is (ter documentatie, we bewegen eraf)

De huidige conduction.nl-illustraties zijn **gedetailleerde flat vector characters** in wat in de stock-industrie bekend staat als "Freepik / Vectorjuice / Upklyak-achtige stijl" — vaak verkocht via Freepik-marketplace, Adobe Stock, Vecteezy. Kenmerken:

- **Filled shapes** (géén line-art zoals ik eerder aannam) — vormen worden gedefinieerd door kleur-contrast, niet door outlines
- **Gedetailleerde gezichten** — uitgewerkte ogen met pupillen, tanden zichtbaar bij glimlach, realistische wenkbrauwen
- **Shading binnen kleur** — haar heeft highlights, kleding heeft vouwen en schaduwen
- **Realistische proporties** — armen en benen hebben normale lengte, niet overdreven stretch
- **Felle kleurvlakken** — kobalt-blauw kleding, rode vesten, geel-oranje accenten
- **Getilte gekleurde achtergrondrechthoeken** — lichtblauw, geel, oranje parallellogrammen achter de figuren
- **Bestaande hexagon-portretten** — in de hex-frames (cobalt achtergrond) is het character-onderdeel van dezelfde stijl

Vergelijkbaar met illustratie-sets als "Upklyak – Business People", "Vectorjuice – Team Scenes", of de betaalde Freepik-vendor-stijl packs.

### Waarom we hier bewust van wegbewegen

Drie inhoudelijke redenen:

1. **Te "stock-foto" qua gevoel.** De huidige illustraties voelen als generieke marketing-stock: de bandleden, de mensen-met-map, de man-die-naar-zichzelf-wijst — ze kunnen op elke SaaS-website of consultancy-brochure staan. Dat botst met het onderscheidende merk dat we bouwen.
2. **Te veel detail voor product-first-positionering.** De realistische gezichten en shading trekken aandacht naar *de mensen*, niet naar *de apps*. Bij een productbedrijf wil je illustraties die het product ondersteunen, niet afleiden.
3. **Niet opnieuw te produceren zonder stockbibliotheek-afhankelijkheid.** Elke keer dat we een nieuwe illustratie nodig hebben, moeten we op de Freepik-marketplace zoeken naar een asset die "ongeveer past". Dat leidt onvermijdelijk tot inconsistentie (licht andere outline, licht andere paletten, licht andere proporties). Een fresh direction moet **reproduceerbaar** zijn — door ons of door een AI.

Plus een eerder argument uit [DESIGN.md](../../DESIGN.md#visuele-richting): bij een **productbedrijf** horen illustraties die **software tonen en abstracte concepten visualiseren**, niet "blije mensen in pakken" — dat was het dienstverlener-tijdperk.

**Het hexagon-portret-concept (zoals in de 3 portret-voorbeelden) blijft overeind.** Het frame + cobalt-achtergrond is goed en on-brand. Alleen het **character-binnenwerk** wordt opnieuw: geen Freepik-flat-vector-character meer, maar de stijl die we hieronder kiezen.

### Fresh direction — vier richtingen om uit te kiezen

Omdat we alles opnieuw doen, ligt het veld open. Hieronder vier genuinely verschillende richtingen met hun eigen feel. Per richting: wat het is, waarom het bij ons zou passen, en wat we ervoor nodig hebben.

#### Richting A — **Hex-first geometric** (mijn aanrader)

**Wat:** illustraties gebouwd uit hexagons en eenvoudige geometrische vormen. Géén (of zeer minimaal) mensen. Concepten worden visueel uitgelegd met hex-composities, verbindingslijntjes, gestapelde vormen.

**Voorbeelden:**
- "Ecosystem" = centrale hex + satellite-hexes + verbindingen
- "Integration" = twee hex-groepen die via een hex-brug verbinden
- "WOO-compliance" = fragmentarisch hex-veld dat consolideert tot één hex-cluster
- "Open source" = hex met open bovenkant, content stroomt eruit

**Palet:** cobalt #21468B dominant, KNVB oranje #F36C21 als accent, wit als adem. Geen andere kleuren.

**Waarom het past:**
- Maximaal merk-consistent — onze hex-motief wordt de illustratie-taal
- Zero stock-foto-risico
- Oneindig schaalbaar — elke nieuwe illustratie is gewoon een nieuwe hex-compositie
- Past bij product-first-positionering (technisch, niet emotioneel)
- Distinctief — niemand anders bouwt zijn illustratie-taal rond hexagons
- Makkelijk produceerbaar: een ontwerper, AI-tool (Midjourney, Figma), of zelfs een technisch-onderlegde developer kan ze maken

**Wat we ervoor nodig hebben:**
- Een master-briefing-tekst (zie onder)
- 4–6 example-illustraties om de stijl te ankeren
- SVG-bibliotheek met herbruikbare hex-primitieven

**Risico:** te koel, te technisch — als het palet te spaarzaam is, kan de site koud aanvoelen. Mitigatie: KNVB-oranje accents en warme Figtree-typografie doen het meeste emotionele werk. Illustraties zijn dan het "rustige rechtopstaande" element.

#### Richting B — **Minimal line-art characters** (karakters-variant)

**Wat:** als we echt menselijke figuren willen tonen (team, samenwerking, klant-sfeer), dan in de absolute tegenpool van de huidige stijl: **pure outline-only**, zero fill, dunne consistente lijnen. Stijlreferentie: Open Peeps of een eigen versie ervan.

**Voorbeelden:**
- Één persoon die naar een laptop kijkt (line-art, cobalt outline)
- Twee mensen die praten (line-art, geen shading)
- Eén persoon in hex-portret-frame (alleen contour zichtbaar tegen cobalt-fill)

**Palet:** cobalt #21468B outline, white fill (niks gekleurd aan de figuur zelf). Oranje accents alleen voor attributen (bv. een map, een laptop-scherm).

**Waarom het past:**
- Warmer dan richting A
- Past bij About-pagina's, testimonials, team-sectie
- Extreem consistent te produceren (lijn-stijl is reproduceerbaar)
- Compleet weg van "Freepik-detail"-feel

**Wat we ervoor nodig hebben:**
- Keuze tussen Open Peeps (CC0, kant-en-klaar) of custom-drawn (meer karakter, meer werk)
- Briefing-tekst voor consistentie

**Risico:** line-art-characters kunnen **saai** worden als ze overal verschijnen — ze leven in hun sobere lijn-esthetiek. Best mix met richting A (concept-illustraties in hex, mens-illustraties in line-art).

#### Richting C — **Editorial / paper-cut** (sophisticated variant)

**Wat:** gelaagde platte vormen die lijken op papiersnijkunst. Elk element is een geometrische vorm (rechthoek, cirkel, hex) met een subtiele textuur of lichte schaduw, die de indruk wekt dat ze op elkaar gelijmd zijn. Stijlreferentie: The New Yorker covers, moderne redactionele illustratie, Tom Froese-achtig.

**Voorbeelden:**
- "Data-catalogi" = gelaagde cirkels en hexagons met subtiele shadow
- "Open source" = een opengewerkte compositie waar je lagen kunt zien

**Palet:** cobalt + oranje + heel subtiele off-white accentlaag. Misschien een textuur-overlay (grain, noise).

**Waarom het past:**
- Sophisticated, volwassen — past bij een MKB-doelgroep die kwaliteit zoekt
- Distinctief — niet veel SaaS gebruikt editorial-stijl
- Duurzaam — editorial-illustraties verouderen minder snel

**Wat we ervoor nodig hebben:**
- Een illustrator of AI-tool die deze stijl kan reproduceren
- Waarschijnlijk duurder en trager te produceren dan richting A

**Risico:** voelt mogelijk te "kunst" voor MKB — kan als "highbrow" ervaren worden door praktisch-ingesteld publiek.

#### Richting D — **Riso / two-color print** (indie-craft variant)

**Wat:** illustraties in de stijl van risograph-prints. Twee kleuren (cobalt + oranje), subtiele offset en grain-textuur, handgemaakt gevoel. Stijlreferentie: moderne OSS-producten als Obsidian, indie dev-sites, zine-cultuur.

**Voorbeelden:**
- Karakters of abstracte scenes, altijd in twee kleuren
- Licht-afwijkende registratie (oranje laag minimaal verschoven t.o.v. cobalt)
- Korrel-textuur over het geheel

**Palet:** strikt cobalt + oranje + wit. Texturen simuleren inkt-overlap.

**Waarom het past:**
- Indie / OSS / crafted-feel — past bij onze community-kant
- Eerlijk en niet-corporate
- Distinctief

**Wat we ervoor nodig hebben:**
- AI-tool (Midjourney met riso-prompt) of een illustrator die dit beheerst
- Textuur-assets (grain overlays) die we als CSS-/SVG-filters consistent toepassen

**Risico:** kan te artsy-fartsy voelen voor conservatievere MKB-doelgroep; kan dated raken als riso-trend verdwijnt.

### Vergelijkingstabel

| Richting | Feel | Productie | Merkconsistentie | Risico |
|---|---|---|---|---|
| **A — Hex-first geometric** | Product, technisch, clean, Dutch-design | Laag — reproduceerbaar door iedereen | Maximaal (hex-motief overal) | Kan koel overkomen |
| **B — Minimal line-art** | Warm, menselijk, friendly | Middel — vraagt consistentie | Goed (cobalt-outline) | Kan saai worden bij overgebruik |
| **C — Editorial** | Sophisticated, redactioneel, volwassen | Hoog — vraagt illustrator | Goed (palet-restrictie) | Kan highbrow voelen voor MKB |
| **D — Riso** | Indie, crafted, OSS-spirit | Middel — vraagt tooling | Goed (twee-kleur-principe) | Kan trendy voelen |

### Mijn aanrader: **Richting A (primair) + B (secundair, alleen voor mensen-momenten)**

Primair **A**, omdat:
- Onze apps zijn producten, geen emotionele diensten — illustraties moeten het product ondersteunen
- Hex-motief wordt zo fundamenteel dat elke nieuwe pagina automatisch "Conduction" voelt
- Laagste productie-friction — een AI of designer kan nieuwe hex-illustraties in minuten maken
- Compleet weg van stock-feel

Secundair **B** voor specifieke momenten waar een mens-aanwezigheid onmisbaar is:
- About-pagina — team-portretten in hex-frames (behoud huidig concept, nieuwe character-stijl)
- Testimonials — klant-avatars in line-art
- Eén of twee plekken op de homepage als het puur-hex te koel wordt

**Niet gelijktijdig C of D** — die zijn elk een heel andere wereld en beperken de reproduceerbaarheid.

### Master-briefing-tekst voor richting A (hex-first geometric)

Bewaar als "master-prompt" voor illustrators en AI-tools. Kan gebruikt in Midjourney, DALL-E, Figma, of als briefing aan een freelance-illustrator.

> *"Vector-based geometric illustrations built from hexagons and simple geometric primitives (circles, rectangles, triangles). No human figures or faces. Pointy-top hexagons only (point at the top). Clean flat shapes, no gradients, no 3D, no shadows except subtle 2D drop-shadows where needed for depth. Colors: cobalt blue (#21468B) as dominant fill or outline; KNVB orange (#F36C21) as accent (maximum 10% of surface); white (#FFFFFF) as background. No other colors. Thin uniform line weight where lines are used (2px at source scale, consistent). Compositions should visualize abstract concepts: ecosystem (central hex with satellite hexes connected by thin lines), integration (two hex-groups joined by a hex-bridge), transparency (hexagons arranged in a visible layered grid), flow (hexagons arranged along a path or funnel). Feel: quiet, competent, Dutch-design-adjacent. Anti-references: no Freepik-style characters, no isometric, no 3D, no faces, no stock-photo feel, no gradients."*

### Master-briefing-tekst voor richting B (minimal line-art characters) — secundair

Voor de momenten waar we mensen moeten tonen:

> *"Minimal outline-only character illustrations. Pure line art, no fill inside the figure (just white). Thin uniform stroke weight (2px at source scale, consistent). Minimal facial features: two dots for eyes, simple curve for mouth, single lines for eyebrows only when expression is needed. Limbs proportional, not stretched. Simple clothing suggested with 2–3 outline details. Colors: cobalt blue (#21468B) outline only; KNVB orange (#F36C21) accent on small objects (a book, a laptop screen, a badge) — never on the figure itself. White (#FFFFFF) background, or placed inside a cobalt-fill hexagon frame for portraits. Style reference: Open Peeps minimalism. No shading, no gradients. One or two figures per illustration, never crowds. Feel: warm but restrained, friendly without being childish."*

### Licentie-overwegingen bij assets

Als we directe librararies gebruiken in plaats van custom:

- **Richting A**: geen bekende library heeft specifiek "hex-first geometric" — moeten we zelf creëren of via AI. Geen licentie-issue.
- **Richting B**: **Open Peeps** is CC0 (volledig vrij, inclusief commercieel gebruik, geen attributie). Dat is de kant-en-klare optie.
- **Richting C**: editorial is typisch custom werk per illustrator. Contract regelt de rechten.
- **Richting D**: riso is typisch custom werk of via Midjourney (check Midjourney-TOS voor commercial use).

Voor richting A + B is er dus geen licensing-probleem.

### Voorbeelden per richting — echte referentie-sites

Per richting: 3–5 echte websites of illustrators waarvan de stijl matcht, plus concrete Conduction-scènes beschreven in die stijl zodat je kunt voorstellen hoe "onze" illustraties eruit zouden zien.

#### Richting A — Hex-first geometric

**Bestaande sites/merken die dit register raken:**

- [honeycomb.io](https://honeycomb.io) — letterlijk hexagon-branding, mooi voorbeeld van hoe ver je kunt komen met alleen hex-vormen
- [supabase.com](https://supabase.com) (vooral de feature-pagina's) — pure geometrische composities, modulair
- [hashicorp.com](https://www.hashicorp.com) — abstracte geometrische tech-illustraties
- [fly.io](https://fly.io) — sterk geometrisch, eenvoudig
- [cloudflare.com](https://www.cloudflare.com) (product-pagina's) — abstracte geometrische vormen als illustratie
- [plausible.io](https://plausible.io) — minimalistisch geometrisch
- [prisma.io](https://www.prisma.io) — technische geometrische visuals

**Pinterest/Dribbble voor "hex-based" en "geometric tech illustration":**

- [dribbble.com/tags/hexagon](https://dribbble.com/tags/hexagon)
- [dribbble.com/tags/geometric-illustration](https://dribbble.com/tags/geometric-illustration)

**Concrete Conduction-scènes in deze stijl:**

- **Homepage hero** — centrale cobalt hex met de C-logo erin; 11 kleinere app-hexen eromheen in een rustige constellatie; dunne cobalt-lijnen verbinden centrum met apps; enkele verbindingen ook app-aan-app; één oranje hex-accent ergens subtiel
- **Solution "WOO-compliance"** — links een fragmentarisch veld van losse, ongekleurde hex-outlines (= versnipperde informatie in silo's); een dunne-lijn-overgang naar rechts; rechts een geconsolideerd hex-cluster in cobalt (= publicatie-platform), één oranje hex bovenop (= de Woo-index harvester die binnenkomt)
- **About-pagina hero** — hex-raster, 5 hexen ingekleurd (onze 5 kernwaardes), verbonden tot een compositie; rest van het raster in outline-only
- **Support-pagina Standard vs Premium** — twee hex-stapels naast elkaar; Standard = 2 hexen gestapeld; Premium = 3 hexen plus een oranje accent-hex bovenop (proactief monitoring-signaal)
- **404** — één eenzame outline-hex "zwevend" links, een geconsolideerd hex-cluster rechts. Copy: *"Lost in the grid."*
- **Footer-achtergrond** — honeycomb-patroon van outline-hexes op 5–8% cobalt-opacity over de hele footer-breedte

**AI-prompt voor Midjourney/DALL-E:**

> *"Flat vector illustration, geometric composition built from hexagons and simple primitives (circles, rectangles, lines). Central large hexagon with smaller hexagons connected by thin lines forming a constellation. Cobalt blue #21468B as primary color, KNVB orange #F36C21 as accent (< 10% of surface), white background. No human figures. No gradients. No 3D. Pointy-top hexagon orientation (point at top). Clean, technical, Dutch-design feel. Style reference: honeycomb.io and supabase.com feature illustrations. --ar 16:9 --style raw"*

#### Richting B — Minimal line-art characters

**Bestaande sites/merken:**

- [openpeeps.com](https://www.openpeeps.com) — de library zelf, met een live preview die de stijl toont
- [icons8.com/illustrations/style--outline](https://icons8.com/illustrations/style--outline) — Icons8's outline-style pagina met honderden voorbeelden
- [storyset.com](https://storyset.com) — filter op "Line Color" variant voor de minimalistische line-versies
- [linear.app](https://linear.app) — soms line-art characters op landings-/feature-pagina's
- [lobste.rs](https://lobste.rs) — illustraties in comments/posts zijn vaak minimal line-art (community-vibe)

**Dribbble-tag:**

- [dribbble.com/tags/open-peeps](https://dribbble.com/tags/open-peeps)
- [dribbble.com/tags/line-illustration](https://dribbble.com/tags/line-illustration)

**Concrete Conduction-scènes in deze stijl:**

- **About-pagina team-portretten** — 4–8 line-art silhouetten, één per teamlid, in de bestaande cobalt hex-frames. Alleen contour zichtbaar, plus minimale facial features (twee stippen = ogen, kort boogje = mond). Eventueel één KNVB-oranje accent per portret (bril, haarlok, baard-hint) om te individualiseren.
- **Testimonials** — klant-avatar in hex-frame naast quote; zelfde line-art-principe. "Karin, IT-manager Gemeente X" — minimal line van een hoofd en schouders, hex-frame.
- **Support-pagina "twee paden"-illustratie** — links een line-art persoon naast een kleine gebouw-outline (Nextcloud-leverancier) met handdruk-motion; rechts een line-art persoon alleen met laptop (self-managed). Compositie toont "jij kiest je pad".
- **Contact-pagina** — één minimal line-art figuur met hand opgestoken in welkom-gebaar, subtiele KNVB-oranje achter een gelezen tablet.

**AI-prompt voor Midjourney/DALL-E:**

> *"Minimal line-art illustration of a single human figure. Outline only, no fill inside the figure. Uniform thin stroke weight. Minimal facial features: two small dots for eyes, simple curve for mouth. Proportional limbs, friendly posture. Cobalt blue #21468B outline only. KNVB orange #F36C21 accent on one small object or element (glasses, a book, a badge). White background. No shading, no gradients, no 3D. Style reference: Open Peeps illustrations. --ar 1:1 --style raw"*

#### Richting C — Editorial / paper-cut

**Bestaande sites/merken:**

- [newyorker.com](https://www.newyorker.com) — klassieke editorial cover-illustraties
- [tomfroese.com](https://www.tomfroese.com) — portfolio van Tom Froese, groot-format geometrisch-editorial
- [malikafavre.com](https://www.malikafavre.com) — Malika Favre, bekend om minimalistisch-editorial geometrie
- [owendavey.com](https://www.owendavey.com) — Owen Davey, retro-editorial, veelgebruikt door redacties
- [charliedavis.co.uk](https://www.charliedavis.co.uk) — Charlie Davis, paper-cut-achtige composities
- Mailchimp's 2018 rebrand (Kind of Collective's werk ervoor) — heeft editorial-elementen

**Dribbble:**

- [dribbble.com/tags/editorial-illustration](https://dribbble.com/tags/editorial-illustration)
- [dribbble.com/tags/paper-cut](https://dribbble.com/tags/paper-cut)

**Concrete Conduction-scènes in deze stijl:**

- **Homepage hero** — een gelaagde paper-cut-compositie: cobalt-achtergrond met een oranje-paper-cut "zon" erboven, daaronder drie gestapelde hex-vormen in verschillende cobalt-tinten (licht/medium/donker), elk met een subtiele drop-shadow zodat ze als losgeknipt papier voelen. Suggestie: "een ecosysteem in lagen."
- **Solution-landing "Zaakafhandeling"** — een abstract burgemeester-bureau-scène in paper-cut: een bureau als rechthoek, gelaagde papierstapels in cobalt-tinten, één document met oranje-hoek dat eruit springt, alles met subtiele shadow-offsets.
- **About hero** — abstracte "Nederland"-paper-cut: horizon van cobalt-heuvels, een stilistische windmolen uit papier geknipt, hex-gestalten in de lucht als wolken. Gecultiveerd, verfijnd. Geen pannekoek-Nederland-kitsch.
- **Blog post headers** — typische editorial-illustraties (gelaagd, geometrisch, subtiel shadowed) van thema-specifieke concepten.

**AI-prompt voor Midjourney/DALL-E:**

> *"Editorial paper-cut illustration. Layered geometric shapes (hexagons, circles, rectangles) with subtle drop shadows creating a sense of cut paper layered on top of each other. Limited palette: cobalt blue #21468B, KNVB orange #F36C21, off-white. Subtle grain or paper texture. Composition feels curated, deliberate, sophisticated. Style reference: The New Yorker covers, Tom Froese, Malika Favre. No human figures unless as silhouettes. Flat but with depth through layering. --ar 3:2 --style raw"*

#### Richting D — Riso / two-color print

**Bestaande sites/merken:**

- [risotto.studio](https://www.risotto.studio) — riso print studio in Edinburgh, met illustraties en prints van eigen werk + klanten
- [riso.party](https://riso.party) — showcase van risograph-prints van kunstenaars wereldwijd
- [peopleofprint.com](https://www.peopleofprint.com/tag/risograph/) — riso-tag van People of Print
- [obsidian.md](https://obsidian.md) — hun illustraties hebben een riso-leunende kwaliteit (grain, twee-kleur-vibe)
- [drawdown.org](https://drawdown.org) — subtiele riso-feel op hun klimaat-website
- Etsy "risograph print" sellers — duizenden voorbeelden

**Pinterest/Dribbble:**

- [pinterest.com/search/pins/?q=risograph+illustration](https://www.pinterest.com/search/pins/?q=risograph%20illustration)
- [dribbble.com/tags/riso](https://dribbble.com/tags/riso)

**Concrete Conduction-scènes in deze stijl:**

- **Homepage hero** — een twee-kleurs-scène van een hex-constellatie, cobalt als primaire inkt, oranje als secundaire met lichte misregistratie (oranje-laag staat 1–2px verschoven t.o.v. cobalt-laag), grain-textuur over het geheel die suggereert dat het geprint is op papier
- **Solutions-sectie** — elk solution-icon als riso-tinten-composite; cobalt + oranje + off-white met subtiel gestippelde textuur
- **Blog/pulse-illustraties** — karakters of scenes (kunnen meer expressief zijn dan in richting A) in twee-kleurs-riso-stijl; één karakter per illustratie, zonder achtergrond of met heel simpele riso-textuur achtergrond
- **Merchandise/gifts** — riso-stijl vertaalt uitstekend naar gedrukte stickers, postkaarten, t-shirts; past bij een OSS-community-gevoel

**AI-prompt voor Midjourney/DALL-E:**

> *"Risograph print style illustration. Two-color print effect with cobalt blue #21468B and KNVB orange #F36C21 inks slightly misregistered (offset 1-2 pixels) creating the characteristic riso look. Subtle grain and paper texture overlay. Limited, somewhat flat and chunky shapes. White or off-white paper background. Indie, crafted, hand-printed feel. Style reference: risograph prints, Risotto Studio, zine aesthetic. --ar 16:9 --style raw"*

### Hoe deze voorbeelden te gebruiken

- **Bij bevestiging van richting A + B** (mijn aanrader): de honeycomb.io- en openpeeps.com-referenties zijn genoeg vertrekpunt. Prompt + 2–3 referentie-screenshots aan de illustrator of AI-tool, en eerste batch is binnen in een dag.
- **Bij twijfel tussen richtingen**: deze lijst biedt genoeg materiaal om op een moodboard (Figma / Miro / Pinterest) te organiseren en één-op-één te vergelijken. Plaats 3–4 voorbeelden per richting naast elkaar, kijk welke het best bij de Conduction-tone en doelgroep past, kies.
- **Als extern illustratie-team gebruikt wordt**: stuur de relevante richting's master-prompt + referenties als brief. Dat geeft ze een concreet houvast om binnen 1–2 iteraties aan te landen.

### Open vraag voor jou

1. **Bevestig je richting A + B als de primair/secundair-combinatie?** Of wil je uit een van de andere richtingen kiezen?
2. **Willen we met een illustrator werken**, of laten we de eerste batch via AI-tools genereren (Midjourney met de master-prompt)?
3. **Hoeveel illustraties hebben we concreet nodig voor de MVP-launch?** Schatting: 8–12 (homepage-values, 3–5 solutions, About-team, 404, één hero-visual). Bevestigen.

Zodra bevestigd, documenteer ik de definitieve richting in BRAND.md en schrappen we dit document in de overgebleven onzekerheid-teksten.

---

## Open punten

- **Illustratie-stijl bevestigen** (zie hierboven)
- **Hex-animation-budget** — hoe veel animatie is gepast? Voor nu: één micro-interactie per sectie (entrance-stagger, hover, count-up). Reduced-motion altijd gehonoreerd. Verdere bijstelling na eerste mock.
- **Hex-tokens in tokens.json** (scope B) — voeg `shape.hexagon.pointy-top` en `shape.hexagon.flat-top` toe als reusable clip-paths, plus `spacing.hex-grid-gap` voor honeycomb-layouts
- **Honeycomb-layout-breakpoints** — op welke viewport stapt honeycomb over naar vertical stack? Voorstel: 768px. Valideren in de eerste mock.
- **Hex-bullet in body-tekst leesbaarheid** — potentieel visueel zwaar voor lange lijsten; bewaak met testen of het niet irriteert bij > 5 items. Anders: hex alleen voor bullet-lijsten tot 4 items, traditionele `•` voor langere.
