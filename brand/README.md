# Conduction Brand Tokens

Machine-leesbare design tokens voor het `conduction-2026` thema. Voor merkwaardes, logo-gebruik en voorbeelden: zie [BRAND.md](../BRAND.md). Voor de rationale achter keuzes: zie [DESIGN.md](../DESIGN.md).

## Bestanden

- [`tokens.json`](./tokens.json) — alle tokens in [W3C DTCG-formaat](https://design-tokens.github.io/community-group/format/) (`$value` / `$type`)
- [`assets/`](./assets/) — SVG-logo's (zie [BRAND.md](../BRAND.md) voor gebruik)

## Scope

**Ronde 1 (huidig):** kleuren + typografie.
**Later:** spacing, radii, shadows, motion, componenttokens. Daar groeien we naartoe zodra apps er tegenaan lopen.

## Structuur

Twee lagen:

1. **Primitieven** (`color.primitive.*`, `typography.primitive.*`) — ruwe waardes, naam beschrijft wát het is, niet waar het gebruikt wordt.
2. **Thema** (`theme.conduction-2026.*`) — semantische tokens die verwijzen naar primitieven. Apps consumeren *alleen* deze laag.

Dit betekent dat een app nooit direct `#21468B` of `color.primitive.blue.cobalt` gebruikt, maar altijd `theme.conduction-2026.color.brand.primary`. Als we de primary-kleur later willen tweaken, hoeft alleen de thema-mapping aangepast — niet elke app.

## Gebruik

### Als CSS custom properties

Genereer met [Style Dictionary](https://amzn.github.io/style-dictionary/) of een vergelijkbare tool:

```css
:root {
  --conduction-color-brand-primary:   #21468B;
  --conduction-color-brand-secondary: #FF7F00;
  --conduction-color-brand-tertiary:  #AE1C28;
  --conduction-color-background-default: #FFFFFF;
  --conduction-color-text-default:    #21468B;

  --conduction-typography-font-family-body: Figtree, system-ui, sans-serif;
  --conduction-typography-font-family-code: 'IBM Plex Mono', ui-monospace, monospace;
}
```

### Als Tailwind config

```js
// tailwind.config.js — uittreksel
import tokens from '../.github/brand/tokens.json' assert { type: 'json' }

export default {
  theme: {
    colors: {
      brand: {
        primary:   tokens.theme['conduction-2026'].color.brand.primary.$value,
        secondary: tokens.theme['conduction-2026'].color.brand.secondary.$value,
        tertiary:  tokens.theme['conduction-2026'].color.brand.tertiary.$value,
      },
    },
    fontFamily: {
      sans: tokens.theme['conduction-2026'].typography['font-family'].body.$value.split(','),
      mono: tokens.theme['conduction-2026'].typography['font-family'].code.$value.split(','),
    },
  },
}
```

### Als Vue / JS import

```js
import tokens from '../../.github/brand/tokens.json'
const primary = tokens.theme['conduction-2026'].color.brand.primary.$value
```

## NL Design System alignment

Conduction volgt NL Design System waar een equivalent token bestaat, en definieert een eigen token waar NLDS niets biedt. Onderstaande mapping is indicatief — zie [DESIGN.md](../DESIGN.md) voor de afwegingen.

| Conduction token | NLDS equivalent | Opmerking |
|---|---|---|
| `theme.conduction-2026.color.brand.primary` | `--nl-color-primary` | Onze waarde (kobaltblauw) is strikt gelijk aan de Nederlandse vlag; NLDS utrecht-theme gebruikt andere tint. |
| `theme.conduction-2026.color.brand.secondary` | — | NLDS heeft geen vaste accentkleur; Conduction kiest `#FF7F00` (windmolen-oranje) om te onderscheiden van Rijkshuisstijl. |
| `theme.conduction-2026.color.brand.tertiary` | — | Eigen token; vermiljoen is officiële NL-vlagkleur, NLDS definieert dit niet. |
| `theme.conduction-2026.color.background.default` | `--nl-color-bg-default` | Gelijk (wit). |
| `theme.conduction-2026.typography.font-family.body` | Theme-afhankelijk in NLDS | Conduction fixeert op Figtree. |

## Fonts

Beide fonts zijn OFL-licensed en gratis beschikbaar via Google Fonts:

- **Figtree** — https://fonts.google.com/specimen/Figtree
- **IBM Plex Mono** — https://fonts.google.com/specimen/IBM+Plex+Mono

Aanbevolen gewichten om te laden: Figtree 400/500/600/700, IBM Plex Mono 400/500.

## Hoe te bijdragen

Tokens wijzigen raakt alle Conduction-apps. Volg [CONTRIBUTING.md](../CONTRIBUTING.md):

1. Open issue met voorstel + rationale (waarom nieuwe/gewijzigde token nodig is)
2. Feature-branch `feature/brand-<kort-onderwerp>` vanaf `main`
3. Tokens aanpassen, [DESIGN.md](../DESIGN.md) updaten met de afweging
4. PR naar `main` met screenshots/voorbeelden van het effect
