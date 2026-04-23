# Icon library — recommendation

Voor functionele UI-iconen (search, arrow, check, external-link, menu, chevron, close, plus) — niet voor logo's (die zitten in de hexagon-wrapper, zie [BRAND.md](../../BRAND.md)).

## TL;DR

**Kies [Lucide](https://lucide.dev).** MIT, tree-shakeable, ~1.400 iconen, de-facto standaard in onze peer-group (Supabase, PostHog en veel andere moderne OSS-productsites). Eén visuele stijl door de hele site, zonder dat we zelf iconen moeten tekenen.

## Afwegingskader

De keuze raakt drie dingen: **stijl-consistentie**, **juridische helderheid**, **praktische wrijving** (bundle-size, i18n/RTL, React-integratie, onderhoud).

| Criterium | Gewicht |
|---|---|
| Consistentie met visuele richting (lijn-gebaseerd, cobalt-vriendelijk, past bij hexagon-thema) | hoog |
| Licentie (moet compatibel zijn met onze EUPL-apps en onze bilingual site) | hoog |
| Tree-shake / bundle-impact (Docusaurus 3.x is Webpack-based, kleine bundles winnen) | middel |
| Onderhoud / active community (geen verlaten projecten) | middel |
| Beschikbaarheid als React-components (Docusaurus is React) | middel |
| Meerdere gewichten/stijlen (extra flexibility voor hero's vs kleine UI) | laag |

## Kandidaten

| Library | Stijl | Licentie | Iconen | Gewichten | React-pkg | Onze beoordeling |
|---|---|---|---|---|---|---|
| **Lucide** | Lijn, 24×24 grid, 2px stroke | ISC (MIT-equivalent) | ~1.400 | 1 (stroke width instelbaar) | `lucide-react` | **Aanbevolen** |
| **Phosphor** | Lijn, meerdere weights | MIT | ~1.200 | 6 (thin/light/regular/bold/fill/duotone) | `@phosphor-icons/react` | Sterk alternatief; kies als we display-iconen met meer karakter willen |
| **Heroicons** | Lijn + solid, 24×24/20×20 | MIT | ~300 | 2 (outline, solid) | `@heroicons/react` | Kleinere set; sterk Tailwind-gebonden — mogelijk limiterend |
| **Feather** | Lijn, 24×24 | MIT | ~280 | 1 | `react-feather` | Voorloper van Lucide, minder actief onderhouden. Niet aanraden. |
| **Material Design Icons (MDI)** | Lijn + fill, 24×24 | Apache-2.0 | ~7.000 | 2 | `@mdi/react` | Te "Google-stijl" — botst met onze cobalt-NL-identiteit. Bovendien: 7k iconen verleidt tot inconsistent gebruik. |
| **Fluent UI System** | Lijn + filled | MIT | ~4.000 | 2 | `@fluentui/react-icons` | Te "Microsoft-stijl" voor een NL-OSS-productbedrijf. |
| **Bootstrap Icons** | Lijn + solid | MIT | ~2.000 | 2 | SVG (geen officiële React-pkg) | Brede set, maar zonder directe React-integratie. Minder aantrekkelijk. |
| **Ant Design Icons** | Lijn + solid + two-tone | MIT | ~800 | 3 | `@ant-design/icons` | Te "enterprise SaaS" en te Ant-specifiek. |
| **Carbon (IBM)** | Lijn + solid | Apache-2.0 | ~2.000 | 2 | `@carbon/icons-react` | Te IBM-stijl. |

## Waarom Lucide

1. **Stijl-fit.** Lijn-iconen met uniforme 2px stroke — past bij Figtree (ronde, rustige letters) en cobalt (donkere, ingetogen primary). Iconen nemen niet de aandacht, ze ondersteunen de UI.
2. **MIT-equivalent licentie.** ISC-licentie, praktisch gelijk aan MIT. Geen conflict met onze EUPL-1.2 apps en geen attributie-ballast.
3. **1.400 iconen is genoeg** zonder verleidelijk overvloedig te zijn. We kunnen een "icon-budget" per pagina hanteren (max. ~8 unieke iconen per pagina) en blijven toch binnen één bibliotheek.
4. **Peer-group-adoptie.** De meeste sites in ons positieve-referentie-rijtje (zie [website.md §9 Referentie-sites](../website.md#referentie-sites-positief--anti)) gebruiken Lucide of een close variant. Dat betekent dat een bezoeker die tussen Supabase, PostHog en ons schakelt een vertrouwde icon-taal tegenkomt.
5. **Stroke-width aanpasbaar.** Voor kleine UI (14–16px): stroke 2.5 voor leesbaarheid. Voor grote iconen (24–32px): stroke 1.5 voor eleganter. Dat dekt hero én microcopy-niveau.
6. **Geen runtime-dependency op een design-system-framework.** Werkt naast Docusaurus zonder swizzling.
7. **Tree-shakeable.** Alleen de iconen die je importeert landen in de bundle — belangrijk voor de bilingual site waar elke kilobyte meetelt.

## Wanneer Phosphor overwegen

Als bij het eerste design-iteratie blijkt dat we per-pagina meer karakter nodig hebben (bv. hero-iconen die duidelijk zichtbaarder moeten zijn dan body-iconen), zijn Phosphor's meerdere gewichten (thin/light/regular/bold/fill/duotone) handig. We kunnen dan één bibliotheek houden voor meerdere gebruikscontexten.

**Switch-criterium:** als we na de eerste twee pagina-mocks merken dat we vaak *twee* icoon-gewichten in dezelfde UI willen, overwegen we Phosphor. Tot die tijd: Lucide.

## Implementatie-notitie

```js
// Voorbeeld in Docusaurus 3.x
import { Download, ArrowRight, Check, X, Menu, Search } from 'lucide-react';

function Button({ label, iconAfter }) {
  return (
    <button className="cta-primary">
      {label}
      {iconAfter && <ArrowRight size={20} strokeWidth={2} aria-hidden="true" />}
    </button>
  );
}
```

**Richtlijnen:**

- **Alt/aria:** Iconen die puur decoratief zijn krijgen `aria-hidden="true"`. Iconen die betekenis dragen krijgen `aria-label` of `title`.
- **Size-scale:** 14, 16, 20, 24, 32, 48 px. Bind aan spacing-tokens in scope B.
- **Stroke-width:** default 2; 2.5 voor ≤16px, 1.5 voor ≥32px.
- **Kleur:** `currentColor` als default, zodat ze de tekstkleur volgen. Actieve/hover-states via CSS custom properties (`--conduction-color-link-hover` voor oranje).

## Wat deze keuze niet dekt

- **App-logo's** blijven in de hexagon-wrapper (zie [BRAND.md](../../BRAND.md#het-conduction-avatar)). Lucide vervangt geen logo's.
- **Illustraties en decoratieve grafieken** — die horen bij illustratie-richting (gap #13 in de one-shot-review), niet bij deze icon-keuze.
- **Emoji's.** Vermijden op de website; iconen geven consistenter resultaat over OS/browsers.

## Escape hatch

Als Lucide voor een specifieke UI-behoefte écht niet werkt (bv. een domein-specifiek icoon dat niet bestaat), dan tekenen we zelf een SVG in dezelfde stijl (24×24 grid, 2px stroke, rounded linecaps). Die custom SVG's komen in `brand/assets/icons/` zodat ze onderdeel zijn van het merk, niet van de webiste-codebase alleen.

Drempel om een icoon zelf te tekenen: minimaal 3 pagina's die hem nodig hebben. Anders: andere UI-oplossing kiezen die binnen Lucide past.
