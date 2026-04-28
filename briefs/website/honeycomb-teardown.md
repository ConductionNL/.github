# Honeycomb.io platform-diagram — technische teardown

Volledige reverse-engineering van hoe Honeycomb hun "explore our platform"-visualisatie heeft gebouwd, inclusief libraries, framework, animaties, en de drie verschillende implementatie-varianten die ze hebben gebruikt. Onderzoek uitgevoerd via Playwright op `https://www.honeycomb.io/` en `https://www.honeycomb.io/platform` op 2026-04-27.

**TL;DR:**
- **Stack**: Next.js (App Router) + Turbopack + Tailwind CSS + React 18+
- **A/B-testing**: VWO (Visual Website Optimizer) — verschillende bezoekers zien verschillende varianten
- **Animatie-libraries**: géén Framer Motion, géén GSAP, géén ScrollTrigger, géén React Spring, géén AOS
- **Wat ze wél gebruiken voor animatie**: pure CSS `transition-colors` (Tailwind) + IntersectionObserver
- **Lottie**: alleen voor de hero-AI-demo (`@lottiefiles/dotlottie-wc` web component), **niet** voor het platform-diagram
- **Drie verschillende diagram-implementaties** in de huidige site (zie hieronder)

---

## 1. Frontend-stack

### Framework & bundler

- **Next.js (App Router)** — bevestigd via JS-chunks in `_next/static/chunks/*.js` patroon en de afwezigheid van `__NEXT_DATA__` (een Pages Router-marker). App Router gebruikt React Server Components.
- **Turbopack** als bundler — bevestigd via `turbopack-7e0989435a23efbe.js` chunk
- **React 18+** — bevestigd door afwezigheid van `data-reactroot` (React 17-marker) en aanwezigheid van moderne fiber-keys
- **Tailwind CSS** — bevestigd via klassen als `mx-auto pt-16 pb-12 lg:py-24`, `transition-colors duration-300`, `hidden lg:flex`, custom prefix-tokens als `text-hc-cobalt`, `bg-hc-sky-100`

### Styling-systeem

- **Tailwind met custom design-tokens**: kleur-naming-conventie `hc-{family}-{shade}` (bv. `hc-sky-900`, `hc-purple-200`, `hc-gold-200`, `hc-red-1000`, `hc-green-100`, `hc-cobalt-*`, `hc-denim`, `hc-gray-*`). Dit is hun eigen Tailwind-config met hun design-tokens als kleur-paletten.
- **Geen CSS-in-JS-library** zichtbaar (geen styled-components, geen emotion-marker)
- **CSS-modules per font** — naming-conventie `roboto_a526148e-module__zhi6Uq__className`, `poppins_b750422f-module__FR8AEW__className` — Next.js' `next/font` met automatische self-hosted Roboto en Poppins

### Marketing/analytics scripts

Meegeladen op iedere pagina (relevant om te weten — *niet* nodig voor de diagram-functionaliteit zelf):

- `recaptcha__en.js` — bot-detectie op formulieren
- `js.hs-banner.com/v2/.../banner.js` — HubSpot
- `cdn.tooltip.io/static/player.js` — Tooltip.io / product-tour
- `tracking-api.g2.com/.../1030168.js` — G2 review tracking
- `cdn.jsdelivr.net/npm/hockeystack@latest/hockeystack-qualified.min.js` — HockeyStack analytics
- `cdn-cookieyes.com/.../banner.js` — CookieYes consent
- `js.hsforms.net/forms/embed/v2.js` — HubSpot forms
- `unpkg.com/@lottiefiles/dotlottie-wc@latest/dist/dotlottie-wc.js` — Lottie web component (voor hero-animatie)
- VWO inline (`window._vwo_code`) — A/B testing engine

### A/B-testing via VWO

De homepage rendert verschillende layouts per bezoeker via VWO (Visual Website Optimizer). Tijdens dit onderzoek constateerden we dat dezelfde URL `https://www.honeycomb.io/` op verschillende sessies verschillende experiences laadt:

- **Variant met grote 3D-isometrische platform-diagram-SVG** — gezien in eerste sessie (zie [`references/ref-a-honeycomb-3d-platform.png`](./references/ref-a-honeycomb-3d-platform.png))
- **Variant met Lottie-AI-demo-hero** — gezien in tweede sessie. De diagram-sectie staat dan op `display: none` op DOM-niveau (geheel verborgen voor deze variant, niet weggelaten)

Implicatie: ze testen welk soort visual-pitch het beste werkt op nieuwe bezoekers. Voor ons relevant: zowel "platform-diagram-as-hero" als "demo-animation-as-hero" zijn legitieme keuzes; Honeycomb test ze tegen elkaar.

### Geen animatie-bibliotheken voor het platform-diagram

Expliciet niet aanwezig in de page-source:

- ❌ Framer Motion (geen `framer-motion`-string, geen `motion-component`-marker)
- ❌ GSAP / TweenMax / TimelineMax
- ❌ GSAP ScrollTrigger
- ❌ React Spring
- ❌ AOS (Animate On Scroll) — geen `data-aos`-attributen
- ❌ tailwindcss-animate plugin
- ❌ Three.js
- ❌ react-three-fiber

### Animatie-mechanismen die ze wél gebruiken

- **CSS `transition-colors`** (Tailwind utility) — 22 keer gebruikt op de pagina. Dit is de kern van de hover-interactie op de pills.
- **Tailwind duration-tokens**: `duration-50`, `duration-200`, `duration-300` — alle drie aanwezig
- **IntersectionObserver** — beschikbaar in de browser-API en gebruikt voor lazy-loading en mogelijk entrance-triggers
- **Lottie web component** (`<dotlottie-wc>`) — **alleen** voor de hero-AI-terminal-animatie aan de top van de pagina, *niet* voor het platform-diagram. Drives door Cloudinary-gehoste JSON-bestand.
- **HTML5 video** (`<video>` met `.mp4`-bron uit Sanity CDN) — gebruikt voor product-demo-clips elders op /platform

---

## 2. Drie verschillende implementaties van hetzelfde "platform-diagram"

Honeycomb heeft over de tijd, en zelfs **gelijktijdig** op verschillende pagina's, drie heel verschillende technieken gebruikt voor wat oppervlakkig dezelfde "platform-overview"-visual lijkt. Dat is leerzaam — niet elke implementatie is even goed.

### Implementatie A — **Inline SVG met `<foreignObject>`-HTML-pills** (de winnende techniek)

Gevonden in de eerste sessie (en op een eerdere versie van de homepage, waarschijnlijk variant A in hun VWO-test).

**Structuur:**

- Eén `<svg viewBox="0 0 1290 780">` direct in de DOM — niet als `<img>` ingeladen
- **119 `<path>`-elementen** die de hex-prism-geometrie opbouwen; per prisma drie paden voor top-vlak / linker-vlak / rechter-vlak met drie kleur-tinten van dezelfde pastel-familie → isometrische diepte zonder echt 3D
- **77 `<rect>`-elementen** met rounded corners voor de externe info-boxes ("Your Data Sources", "60+ Integrations") en pill-containers
- **8 `<foreignObject>`-elementen** — één per categorie-hex. Elk bevat een HTML-subtree (`<div>` + `<a>`-pills). Dit is de cruciale techniek: SVG voor geometrie, HTML-binnen-SVG voor de tekst-labels
- **87 elementen** met `cursor: pointer` — grotendeels de pills
- **Pills zijn `<a>`-elementen** die naar sub-pagina's linken (`/platform/distributed-tracing`, `/platform/canvas`, etc.). Echte navigatie-links, geen JS-handler-only.
- **Hover-interactie** = pure CSS, via Tailwind `transition-colors duration-150` op pill-classes. Bij hover wisselt het pill-background een toon binnen de categorie-kleurfamilie. **Geen JS** voor deze animatie.
- **Categorie-kleuren** via Tailwind-tokens: `bg-hc-sky-100`, `bg-hc-purple-200`, `bg-hc-gold-200`, `bg-hc-red-100`, `bg-hc-green-200`, `bg-hc-gray-200`. Hun design-systeem heeft 6+ kleurfamilies, elk met `100`-`1000`-shades.

**Voorbeeld-pseudocode** (gereverse-engineerd):

```html
<svg viewBox="0 0 1290 780" class="lg:w-[1000px] xl:w-[1280px]">
  <!-- Statische hex-prism-geometrie als groep paden -->
  <g class="hex-prism hex-data-foundation">
    <path d="M650 250 L750 250 L800 320 L750 390 L650 390 L600 320 Z"
          fill="var(--hc-green-100)"/>  <!-- top face -->
    <path d="..." fill="var(--hc-green-300)"/>  <!-- left face -->
    <path d="..." fill="var(--hc-green-500)"/>  <!-- right face -->
  </g>
  <g class="hex-prism hex-realtime-access">
    <!-- 3 paths -->
  </g>
  <!-- ... 6 totaal ... -->

  <!-- Externe info-boxes als rects -->
  <g class="data-sources-box">
    <rect x="40" y="490" width="180" height="240" rx="12"
          fill="var(--hc-gray-50)" stroke="var(--hc-gray-200)"/>
  </g>

  <!-- Pill-clusters per categorie via foreignObject -->
  <foreignObject x="650" y="350" width="340" height="220">
    <div xmlns="http://www.w3.org/1999/xhtml" class="flex flex-col items-end gap-1.5">
      <a href="/platform/distributed-tracing"
         class="font-roboto pointer-events-auto rounded-lg border px-2 py-1 text-[10px]
                font-semibold transition-colors text-hc-sky-900 bg-hc-sky-100 border-hc-sky-200
                hover:bg-hc-sky-200 hover:border-hc-sky-300">
        Distributed Tracing
      </a>
      <a href="/platform/log-analytics" class="...">Log Analytics</a>
      <a href="/platform/metrics" class="...">Metrics</a>
      <span class="category-label">REALTIME ACCESS</span>
    </div>
  </foreignObject>
  <!-- ... 7 meer foreignObjects ... -->

  <!-- Dashed flow-paths tussen elementen -->
  <path d="M220 600 L380 550 ..." stroke="var(--hc-cobalt-400)"
        stroke-dasharray="4 4" fill="none"/>
</svg>
```

**Voordelen:**

- ✅ **Crisp op elke schaal** (pure vector)
- ✅ **Accessibility**: pills zijn echte `<a>` met focus-states, screen-reader-leesbaar, keyboard-navigeerbaar via Tab
- ✅ **SEO**: tekst staat in DOM, niet gebakken in een raster-image
- ✅ **i18n**: HTML-tekst is vertaalbaar via reguliere mechanismen
- ✅ **Editable in code**: label wijzigen = HTML aanpassen; kleur wijzigen = Tailwind class
- ✅ **Geen JS-library** voor animatie nodig
- ✅ **Klein bundle-impact** — paden zijn geometrisch en gecomprimeerd, foreignObject-content is kort
- ✅ **Real navigation**: pills zijn `<a href>` — werkt zonder JS, prerenderbaar, deelbaar

**Nadelen:**

- Vraagt design-werk voorin: hex-prism-geometrie hand-tekenen (eenmalig)
- foreignObject heeft enkele oude-browser-incompatibiliteiten (irrelevant voor moderne stacks)
- Vraagt zorgvuldige a11y-test (focus-visibility, screen-reader-volgorde)

### Implementatie B — **Static SVG-bestand als `<img>` ingeladen** (huidige /platform — schadelijk)

Gevonden op `https://www.honeycomb.io/platform` op 2026-04-27.

**Structuur:**

- Een `<img src="https://cdn.sanity.io/.../388759a046cdf4b61e9074ee49d327ff956787f2-1440x415.svg">` in de DOM
- Het SVG-bestand zelf is **361 KB groot**
- Bevat **995 `<path>`-elementen** — alle tekst (DISTRIBUTED TRACING, LOG ANALYTICS, etc.) is geconverteerd naar **paden** (geen `<text>`-elementen!)
- 82 `<rect>`-elementen, 8 `<clipPath>`'s
- **0 `<text>`-elementen, 0 `<foreignObject>`-elementen**

**Daarboven:** een **separate, lege `<svg>` overlay** (1270×1270) die programmatisch dashed flow-lijnen toevoegt voor animatie. Dat is hun trick om de statische SVG levend te laten lijken zonder hem opnieuw te bouwen.

**Voor- en nadelen:**

- ✅ **Snel te bouwen** vanuit Figma (Export-as-SVG)
- ✅ **Geen logica nodig** in code — gewoon een asset
- ❌ **361 KB asset** voor één visual — te groot
- ❌ **Tekst is paden** → geen accessibility, geen screen-reader-leesbaarheid
- ❌ **Geen i18n** mogelijk zonder de SVG opnieuw te exporteren per taal
- ❌ **Geen interactieve hover** mogelijk — `<img>` heeft geen interne hit-detection
- ❌ **Geen SEO-waarde** voor de termen in het diagram
- ❌ **Geen native links** vanuit het diagram naar sub-pagina's

**Conclusie**: dit is wat Honeycomb *nu* op /platform heeft, maar het is **inferieur** aan implementatie A. Wij moeten dit niet kopiëren.

### Implementatie C — **Lottie-animatie via `<dotlottie-wc>`** (homepage hero, AI-demo)

Gevonden in tweede sessie op `https://www.honeycomb.io/` (variant zonder de SVG-diagram).

**Structuur:**

- Een `<dotlottie-wc autoplay loop src="https://res.cloudinary.com/spiralyze/.../Homepage_animation.json">` web component
- Library: `@lottiefiles/dotlottie-wc` van unpkg
- JSON-bestand uit Cloudinary
- Gebruikt voor de **hero-AI-terminal-animatie** (Claude Code achtige terminal die tekst typt) — **niet voor het platform-diagram**

**Voor- en nadelen:**

- ✅ **Rijk geanimeerd** — tekst-typing-effect, code-output-rolling, etc.
- ✅ **JSON-formaat** — schaalt en compresseert beter dan video
- ✅ **Web-component** integreert zonder framework-koppeling
- ❌ **Niet accessible** — Lottie-content is niet screen-reader-leesbaar (zonder extra werk)
- ❌ **Niet interactief** zonder programmatic control
- ❌ **Externe library + asset** loaded; bundle-impact

Voor ons: relevant als we ooit een "demo-loop"-animatie willen tonen (niet voor het platform-diagram, wel mogelijk voor "live-screencast"-illustraties later).

---

## 3. Welke implementatie wij overnemen — en waarom

**Wij gaan voor implementatie A** (inline SVG met `<foreignObject>`-HTML-pills), zoals al vastgelegd in [`visual-motifs.md`](./visual-motifs.md#implementatie--bevestigd-via-reverse-engineering-van-honeycombio-2026-04-23) en [`claude-design-handoff.md`](./claude-design-handoff.md).

Reden: A is de enige variant die **alle** voordelen van het platform-diagram-concept levert (visuele helderheid + accessibility + SEO + i18n + interactivity), zonder de nadelen van B (gigantisch raster-asset, geen tekst) of C (Lottie-overkill voor een statisch-met-hover-diagram).

**Bouwstack** (parallel aan Honeycomb's Next.js-stack maar in onze Docusaurus 3.x context):

| Onderdeel | Honeycomb | Conduction |
|---|---|---|
| Framework | Next.js App Router | Docusaurus 3.x (React-based) |
| Bundler | Turbopack | Webpack (Docusaurus default) |
| Styling | Tailwind CSS met `hc-*`-tokens | CSS custom properties uit `brand/tokens.json` (geen Tailwind verplicht) |
| Animatie | CSS `transition-colors` + IntersectionObserver | Idem — geen JS-animatie-lib nodig |
| Pills | Tailwind class-set + `<a href>` | Eigen CSS-class + `<a href>` |
| Geometrie | Inline SVG met hand-getekende paden | Idem — Claude Design tekent op basis van Honeycomb-referentie + onze 6 categorie-mapping |
| Externe overlays | `<foreignObject>` met HTML | Idem |

**Geen JS-animatie-library nodig.** Dat is een belangrijk inzicht: voor het diagram is *pure CSS* genoeg. Wij blijven daarmee licht (geen Framer Motion, geen GSAP toevoegen aan de bundle).

**Wel gebruiken we:**

- **IntersectionObserver** voor entrance-triggers (zachte fade-in van het diagram als het in beeld komt). Standaard browser-API, geen library.
- **CSS `prefers-reduced-motion`** om animaties uit te zetten voor users die dat instellen.
- **CSS custom properties** voor categorie-kleuren, gevoed uit `brand/tokens.json` (scope B uitbreiding zal `color.category.foundation`, `color.category.integration`, etc. toevoegen).

---

## 4. Praktische bouw-checklist voor Claude Design / illustrator

Wanneer Claude Design (of een illustrator) onze versie bouwt, volgt het deze stappen:

### Stap 1 — Compositie schetsen

1. Open [`references/ref-a-honeycomb-3d-platform.png`](./references/ref-a-honeycomb-3d-platform.png) als visuele anker
2. Vervang Honeycomb's 6 categorieën door onze 6 (zie [`visual-motifs.md`](./visual-motifs.md#platform-overview-pattern--honeycomb-stijl-als-hero)):
   - Data Foundation (groen) — OpenRegister, OpenCatalogi
   - Integration (geel) — OpenConnector
   - Documents (rood/roze) — DocuDesk
   - Case & Process (blauw) — Procest, ZaakAfhandelApp, PipelinQ
   - Insights & Dashboards (paars) — MyDash, SoftwareCatalog
   - Design & Theming (grijs) — NLDesign, LarpingApp
3. Externe boxes: links "Je bestaande systemen" (Nextcloud, BAG, BRK, PDOK), rechts "Integraties" (Nextcloud app store, gov-portals, e-mail, LLM-tools)

### Stap 2 — SVG-paden bouwen

1. Kies één hex-prism-template (3 paden: top, links, rechts) op vaste afmetingen
2. Dupliceer en plaats 6 keer in de viewBox `0 0 1290 780`
3. Per categorie: vul de drie paden met drie tinten van dezelfde pastel-familie (bv. groen-100, groen-300, groen-500 voor Data Foundation)
4. Voeg externe `<rect>`-boxes toe voor Your Systems / Integrations
5. Voeg dashed `<path>`-connectoren toe (`stroke-dasharray="4 4"`) tussen elementen die data-flow tonen

### Stap 3 — `<foreignObject>` overlays per categorie

Voor elke categorie-hex, één `<foreignObject>` met HTML-pills:

```html
<foreignObject x="..." y="..." width="..." height="...">
  <div xmlns="http://www.w3.org/1999/xhtml" class="pill-cluster">
    <a href="/apps/openregister" class="pill pill-foundation">OpenRegister</a>
    <a href="/apps/opencatalogi" class="pill pill-foundation">OpenCatalogi</a>
    <span class="category-label">DATA FOUNDATION</span>
  </div>
</foreignObject>
```

### Stap 4 — CSS

```css
.pill {
  font-family: 'Figtree', system-ui, sans-serif;
  font-size: 10px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid;
  cursor: pointer;
  transition: background-color 150ms, border-color 150ms;
  text-decoration: none;
  pointer-events: auto;  /* belangrijk: standaard SVG-pointer-events kunnen blokkeren */
}
.pill-foundation {
  color: var(--color-green-900);
  background: var(--color-green-100);
  border-color: var(--color-green-200);
}
.pill-foundation:hover {
  background: var(--color-green-200);
  border-color: var(--color-green-300);
}
/* ... per categorie */

.category-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  color: var(--color-cobalt-700);
}
```

### Stap 5 — Optioneel: entrance-animatie via IntersectionObserver

```js
const diagram = document.querySelector('.platform-diagram svg');
const observer = new IntersectionObserver((entries) => {
  entries.forEach(e => {
    if (e.isIntersecting) {
      diagram.classList.add('visible');
      observer.unobserve(e.target);
    }
  });
}, { threshold: 0.3 });
observer.observe(diagram);
```

```css
.platform-diagram svg {
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 600ms ease-out, transform 600ms ease-out;
}
.platform-diagram svg.visible {
  opacity: 1;
  transform: translateY(0);
}

@media (prefers-reduced-motion: reduce) {
  .platform-diagram svg {
    transition: none;
    opacity: 1;
    transform: none;
  }
}
```

### Stap 6 — A11y-checklist

- [ ] Pills zijn `<a>`-elementen met `href` — focusable via Tab
- [ ] Pills hebben zichtbare focus-state (oranje ring per onze conventie)
- [ ] SVG heeft `role="img"` en `aria-labelledby` naar een `<title>` met beschrijving
- [ ] Reduced-motion gerespecteerd
- [ ] Kleur-contrast op pills is WCAG AA (cobalt-tekst op pastel-achtergrond moet ≥ 4.5:1 zijn)
- [ ] `<foreignObject>`'s hebben `lang`-attribuut zodat screen-readers de uitspraak goed kiezen
- [ ] Tekst op pillen zelf is leesbaar door Tab-navigatie

---

## 5. Wat dit betekent voor de Claude Design handoff

[`claude-design-handoff.md`](./claude-design-handoff.md) bevat al de kern-instructie. Eén toevoeging na deze diepere analyse:

> **Stack-vrijheid**: het diagram heeft *geen* JS-animatie-library nodig. Honeycomb (de referentie) gebruikt enkel CSS `transition-colors` en `IntersectionObserver`. Voeg alsjeblieft *geen* Framer Motion / GSAP / anim-library toe — dat blaast onze bundle op zonder echte winst.

Dit kan de designer impliciet "veiliger" maken in keuzes — gewoon CSS, geen library-reach. Update voer ik direct door in `claude-design-handoff.md` als footnote bij de stack-constraints.

---

## 6. Open vragen / wat we niet hebben kunnen verifiëren

- **De originele bron-SVG** van implementatie A (de interactieve variant) hebben we niet kunnen pakken; we werken op basis van het screen-rendering en DOM-inspection. Voor exacte path-kopie is een betere snapshot nodig of we tekenen vanuit nul (wat sowieso de bedoeling is — Conduction-versie hoort eigen geometrie te hebben).
- **Honeycomb's design-token-config** is privé. Wij baseren onze category-pastels op eigen overwegingen (zie [`visual-motifs.md`](./visual-motifs.md#platform-overview-pattern--honeycomb-stijl-als-hero)).
- **Animatie van de dashed flow-lines** (de stippeltjes die langs de connectoren bewegen) — niet onderzocht. Mogelijk een SVG `<animate>` of een CSS keyframe-animatie op `stroke-dashoffset`. Onze versie kan starten met *statische* dashed lines en later eventueel animatie toevoegen.

---

## 6.5. Animatie-analyse — wat beweegt er werkelijk? (2e sessie deep-dive)

In een vervolgonderzoek (sessie van 2026-04-27) hebben we via Playwright **alle CSS-keyframes en transitions** in de pagina geïnventariseerd, **elk dashed-pad in het diagram geïnspecteerd**, en de **default state vs hover state** vergeleken. Conclusie: het diagram is opvallend stil. Vrijwel alle "beweging" zit in één pure-CSS interactie.

### Wat we vonden

**Globale CSS @keyframes-rules in de pagina** (gedefinieerd, maar bijna allemaal voor andere onderdelen):

| Keyframe | Waar gebruikt |
|---|---|
| `swiper-preloader-spin` | Carousel-spinners |
| `logoScroll` / `logoScrollReverse` | De marquee van klant-logo's onderaan |
| `spin` | Loading-spinners |
| `accordion-down` / `accordion-up` | Radix-UI accordion-componenten elders |
| `fadeIn`, `fadeInScale`, `ring` | Generieke utility-klassen, **niet** toegepast op het diagram |

Geen enkele van deze keyframes is op het diagram zelf actief.

**Op het platform-diagram zelf** vonden we exact deze CSS:

- **Pill-spans** (`<span>` met Tailwind-klasse `transition-colors duration-150`):
  - `transition-property: color, background-color, border-color, outline-color, text-decoration-color, fill, stroke, --tw-gradient-from, --tw-gradient-via, --tw-gradient-to`
  - `transition-duration: 0.15s`
  - **Geen `animation`** (animationName: `none`)
- **Hex-prism path-elementen** (`<path>` met Tailwind-klasse `transition-all group-hover:opacity-100`):
  - `transition-property: all`
  - `transition-duration: 0.15s`
  - **Geen `animation`**
  - Default `opacity` < 1; bij `:hover` op de groepscontainer wordt `opacity` 1
- **Dashed flow-paden** (8 stuks): `stroke-dasharray: 2.41px, 3.85px`, **`stroke-dashoffset: 0px`**, **geen animation**, **geen transitie**. Statische dashed-lijntjes zonder beweging.
- **Geen `<circle>`-elementen** in het diagram (de "dotjes" die je in screenshots ziet zijn de korte segmenten van de stroke-dasharray, niet aparte circles)
- **Geen `<animate>` / `<animateTransform>` / `<animateMotion>` SMIL-elementen** in de SVG
- **Geen `IntersectionObserver`-class-toggle** op de SVG: er is geen `data-aos`, geen `.in-view`, geen entrance-fade

### Het werkelijke "magische" effect: spotlight via `group-hover`

Het ene effect dat het diagram echt **levend** maakt zit in de Tailwind **`group-hover:opacity-100`** modifier op de hex-prism-paden:

1. In default-state staan alle hex-prism-paden op een **lagere opacity** (zo'n 60–70%) — alle hexen zijn licht-translucent
2. Elke hex-groep is een `<g class="group">` (of een `<a class="group">`) met daarbinnen zowel de hex-paden als de foreignObject-pills
3. Bij hover op enige content binnen de group (een pill, of de hex zelf) wordt de **hele groep** als hovered geïnterpreteerd, en de paden gaan via `group-hover:opacity-100` naar 100% opacity
4. Resultaat: de gehover-de hex springt uit, de andere hexen voelen alsof ze "opzij stappen" (niet écht; ze veranderen niet, maar de relatieve helderheid van de gehoverde hex maakt dat zo)
5. Transitie-tijd: 0.15s — kort genoeg om snappy te voelen

Vergelijk de twee screenshots:

| Default (alle hexes ~70%) | Hover op "Distributed Tracing" (REALTIME ACCESS-hex naar 100%) |
|---|---|
| ![Default state](./references/ref-a-honeycomb-default-state.png) | ![Hover state](./references/ref-a-honeycomb-hover-state.png) |

In de hover-screenshot is de blauwe REALTIME ACCESS-hex (links-boven) duidelijk feller, terwijl de andere hexen relatieve "achtergrond" worden. Dit is de **enige** echte interactie van het diagram.

### Wat er dus NIET gebeurt (ondanks visuele suggestie)

- ❌ Geen flow-line-animatie — de dashed connectoren zijn statisch, geen bewegende stippels
- ❌ Geen entrance-fade-in als je naar het diagram scrollt
- ❌ Geen ademhalings-loop op de hexen (puls, glow, etc.)
- ❌ Geen circle-dots die door de paden bewegen
- ❌ Geen automatische cyclus die elk hex om beurten "demonstreert"
- ❌ Geen Lottie / Framer Motion / GSAP / SVG-SMIL ergens betrokken

**De totale animatie-budget op het hele diagram bedraagt 0.15s color-transitions plus 0.15s opacity-transitions.** Dat is alles.

### Wat dit voor ons betekent

Goed nieuws: het effect is **trivial te reproduceren** met Tailwind (of plain CSS). Geen library, geen JS-driver. Concrete recept voor onze versie:

```html
<svg viewBox="0 0 1290 780" class="platform-diagram">
  <!-- Per categorie een group; default opacity lager -->
  <a href="/apps/openregister" class="group hex-data-foundation">
    <path class="hex-path top transition-opacity duration-150
                 opacity-70 group-hover:opacity-100"
          d="..." fill="var(--cat-foundation-100)"/>
    <path class="hex-path left transition-opacity duration-150
                 opacity-70 group-hover:opacity-100"
          d="..." fill="var(--cat-foundation-300)"/>
    <path class="hex-path right transition-opacity duration-150
                 opacity-70 group-hover:opacity-100"
          d="..." fill="var(--cat-foundation-500)"/>
    <foreignObject x="..." y="..." width="..." height="...">
      <div xmlns="http://www.w3.org/1999/xhtml" class="pills">
        <span class="pill transition-colors duration-150">OpenRegister</span>
        <span class="pill transition-colors duration-150">OpenCatalogi</span>
        <span class="category-label">DATA FOUNDATION</span>
      </div>
    </foreignObject>
  </a>
  <!-- ... 5 meer category groups ... -->

  <!-- Statische dashed flow-paden, geen animatie -->
  <path d="..." stroke="var(--color-cobalt-300)"
        stroke-dasharray="2.41 3.85" fill="none"/>
</svg>
```

Plus optionele entrance-animatie als we die wel willen (Honeycomb heeft 'm niet, maar wij mogen 'm toevoegen):

```css
@media (prefers-reduced-motion: no-preference) {
  .platform-diagram {
    opacity: 0;
    transform: translateY(20px);
    transition: opacity 600ms ease-out, transform 600ms ease-out;
  }
  .platform-diagram.in-view {
    opacity: 1;
    transform: translateY(0);
  }
}
```

```js
new IntersectionObserver((entries) => {
  entries.forEach(e => e.isIntersecting && e.target.classList.add('in-view'));
}, { threshold: 0.3 }).observe(document.querySelector('.platform-diagram'));
```

Dat zijn ~10 regels JS plus 8 regels CSS — geen library nodig.

### Het "moving dots"-misverstand

Op de screenshots lijken er soms dotjes langs de dashed lines te liggen. Het gebruikelijke instinct is "die zullen bewegen!" — maar nee. Het is gewoon de stroke-dasharray die elke gap-pixels-met-color-pixels-streepje rendert. Voor een viewer-met-bewegingsperceptie kan dit **statisch lijnen-met-puntjes** zijn, en niet "dots that flow".

Als wij wél een flow-animatie willen (om "data stroomt door het systeem" te suggereren), kunnen we die simpel toevoegen via:

```css
.flow-line {
  stroke-dasharray: 2.41 3.85;
  animation: flow 1.2s linear infinite;
}
@keyframes flow {
  to { stroke-dashoffset: -6.26; }  /* 2.41 + 3.85 = één periode */
}
@media (prefers-reduced-motion: reduce) {
  .flow-line { animation: none; }
}
```

Dat is **8 regels CSS** voor een effect dat Honeycomb niet eens gebruikt. Wij kunnen optioneel meer beweging dan zij toevoegen — voor *minder* gebruikersmoeite (geen JS-library). Onze keuze.

### Aanbeveling — wat we wél/niet doen

| Effect | Honeycomb | Ons advies | Implementatie |
|---|---|---|---|
| Spotlight bij hover op category | ✅ | ✅ Overnemen | `group-hover:opacity-100` |
| Color-transition op pills | ✅ | ✅ Overnemen | `transition-colors duration-150` |
| Entrance-fade-in bij scroll | ❌ | ✅ Toevoegen (subtle) | IntersectionObserver + 600ms transition |
| Flow-line motion | ❌ | ❓ Optioneel — alleen als het de "data-flow"-boodschap echt versterkt | `@keyframes` op `stroke-dashoffset`, 8 regels CSS |
| Hex-pulsation / breathing | ❌ | ❌ Niet doen — over-ge-animeerd | — |
| Lottie of Framer Motion | ❌ | ❌ Niet toevoegen | — |
| Auto-rotate categorie-cyclus | ❌ | ❌ Niet doen — afleidend | — |

Lichte hand. Eén of twee subtiele animaties zijn meer dan genoeg.

---

## 7. Conclusie in één zin

Honeycomb's krachtige platform-diagram is **een hand-getekende inline SVG met HTML-pills via `<foreignObject>`, gestyled met Tailwind CSS, geanimeerd met pure CSS `transition-colors`, en gehost binnen een Next.js App Router-app**. Geen Framer Motion, geen GSAP, geen 3D-engine. Wij kunnen het op identieke wijze bouwen binnen Docusaurus 3.x — en *moeten* dat doen, want de "static SVG-as-img"-variant die ze tegenwoordig op /platform tonen is technisch inferieur (361 KB asset, geen accessibility, geen interactiviteit).
