# Conduction Brand Guide

Dit document beschrijft de Conduction huisstijl: wie we zijn, hoe we eruitzien, en hoe je het merk consistent toepast over al onze apps, documentatie en communicatie.

Voor de **rationale** achter onze keuzes: zie [DESIGN.md](./DESIGN.md).
Voor **machine-leesbare tokens**: zie [`brand/tokens.json`](./brand/tokens.json).

---

## Wie we zijn

Conduction is een **Nederlands open-source-bedrijf** dat ICT-oplossingen bouwt voor overheid en maatschappelijk domein. Onze identiteit leunt bewust op Nederlandse kernwaardes:

- **Trots Nederlands.** We ontwerpen vanuit Nederlandse standaarden (NL Design System, Common Ground, API-principes) en dragen dat uit.
- **Innovatief.** We lopen voorop in open source, API-first architectuur, en federatieve datamodellen.
- **Handelsgedreven.** Pragmatisch, doelgericht, resultaatgericht. Oplossingen die werken, niet vertoningen.
- **Penny-wise.** Open source, hergebruik, zuinig met publieke middelen — dezelfde discipline die onze software kenmerkt.
- **Betrouwbaar.** Stabiel, transparant, voorspelbaar. De dieper-blauwe huisstijl onderstreept dat.

---

## Logo

### Het Conduction avatar

Het Conduction-avatar bestaat uit een **dubbele zeshoek** (hexagon-in-hexagon) met daarin een C-vorm. De buitenste zeshoek is het omkapsel dat ook om applicatielogo's komt — dit patroon is herkenbaar en terugkerend door ons hele merk.

| Versie | Gebruik | Bestand |
|---|---|---|
| **Kobalt op wit** (default) | Op lichte achtergronden, in documenten, op de website | [`brand/assets/avatar-conduction-on-white.svg`](./brand/assets/avatar-conduction-on-white.svg) |
| **Wit op kobalt** (inverse) | Op donkere achtergronden, hero-secties, social avatars | [`brand/assets/avatar-conduction-on-blue.svg`](./brand/assets/avatar-conduction-on-blue.svg) |
| **Transparant** (flexibel) | Generiek gebruik met eigen achtergrond | [`brand/assets/avatar-conduction.svg`](./brand/assets/avatar-conduction.svg) |

### Applicatielogo's: de hexagon-wrapper

Applicaties (OpenRegister, OpenCatalogi, OpenConnector, DocuDesk, …) krijgen hun eigen iconografie **binnen** de kenmerkende zeshoek-wrapper. Zo blijft het Conduction-merk zichtbaar zonder dat app-identiteiten in elkaar overlopen.

Richtlijnen:
- De wrapper is altijd een zeshoek.
- App-icon mag in de primary-brand-kleur, tertiary-brand-kleur of wit — nooit in oranje (oranje is accent, geen kernkleur).
- Minimale grootte: 32×32px. Kleiner wordt de zeshoek onleesbaar.

### Do's

- ✅ Gebruik SVG waar mogelijk — schaalt altijd scherp
- ✅ Respecteer minimaal 1/4 van de hoogte als witruimte rondom het avatar
- ✅ Gebruik altijd de officiële kleuren (`#21468B`, `#FFFFFF`)

### Don'ts

- ❌ Geen andere tinten blauw toepassen op het logo
- ❌ Niet roteren, schuintrekken of outlinen
- ❌ Niet op drukke fotografische achtergronden plaatsen zonder witte/blauwe fond
- ❌ De zeshoek-wrapper niet vervangen door een andere vorm

---

## Kleurpalet

Onze kleuren zijn gebaseerd op de **officiële Nederlandse vlagkleuren**.

| Rol | Naam | Hex | RGB | Gebruik |
|---|---|---|---|---|
| **Primary** | Kobaltblauw | `#21468B` | 33, 70, 139 | Merk, links, CTA's, koppen |
| **Secondary** | Windmolen-oranje | `#FF7F00` | 255, 127, 0 | Accenten, highlights, hover |
| **Tertiary** | Helder vermiljoen | `#AE1C28` | 173, 28, 40 | Spaarzaam — attentie, error-state |
| **Background** | Wit | `#FFFFFF` | 255, 255, 255 | Default achtergrond |

### Waarom deze drie?

- **Kobaltblauw** is officieel de blauwtint van de Nederlandse vlag. Donkerder dan onze oude lichtblauw, straalt betrouwbaarheid en stabiliteit uit.
- **Oranje** is expliciet *niet* het Rijkshuisstijl-oranje — we kiezen windmolen-oranje als onderscheidende accentkleur. Zo blijven we herkenbaar als bedrijf, niet als overheid.
- **Vermiljoen** is de officiële rode vlagkleur. Spaarzaam in te zetten voor attentie en error-states.

### Proportie

Richtlijn voor balans in vlakverdeling:

- **70%** wit (achtergrond, ademruimte)
- **20%** kobaltblauw (merk, structuur, tekst)
- **8%** oranje (accent, hover, highlight)
- **2%** vermiljoen (uiterst spaarzaam)

Oranje en vermiljoen zijn **krachtige** kleuren — gebruik ze als bijspeler, niet als hoofdrolspeler.

### Do's

- ✅ Gebruik cobalt voor structuur en primaire acties
- ✅ Gebruik oranje voor attentie zonder alarm (hover, nieuwe badge, highlight)
- ✅ Gebruik vermiljoen alléén voor echte attentie (error, destructieve actie)

### Don'ts

- ❌ Meng oranje en rood nooit in hetzelfde oppervlak
- ❌ Gebruik geen oranje voor grote vlakken (hero-achtergrond, sidebar)
- ❌ Introduceer geen nieuwe tinten blauw — alles gaat via `theme.conduction-2026.color.brand.primary`

---

## Typografie

### Lettertypes

| Rol | Font | Licentie | Bron |
|---|---|---|---|
| **Body + headings** | Figtree | SIL Open Font License (OFL) | [Google Fonts](https://fonts.google.com/specimen/Figtree) |
| **Code + monospace** | IBM Plex Mono | SIL Open Font License (OFL) | [Google Fonts](https://fonts.google.com/specimen/IBM+Plex+Mono) |

### Karakter

**Figtree** is een ronde, rustige, humanistische sans-serif. Warmer dan Inter, professioneler dan Nunito, moderner dan Source Sans. Past bij onze "trots Nederlands, handelsgedreven" identiteit.

**IBM Plex Mono** is een rustige monospace met iets warme vormen — harmonieus naast Figtree, zonder scherp technisch randje.

### Fallback stack

Als de webfont niet laadt, vallen we terug op systeemfonts — geen Times New Roman, nooit:

```
Figtree, system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif
'IBM Plex Mono', ui-monospace, 'SF Mono', Menlo, Consolas, monospace
```

### Schaal

Zie [`brand/tokens.json`](./brand/tokens.json) voor de exacte waardes. Ramp: 12 / 14 / 16 / 18 / 20 / 24 / 32 / 40 / 48 px. Gewichten: 400 (regular), 500 (medium), 600 (semibold), 700 (bold).

### Do's

- ✅ Headings in 600/700, body in 400
- ✅ Line-height 1.5 voor body, 1.2 voor koppen
- ✅ Laad alleen de gewichten die je daadwerkelijk gebruikt (400, 500, 600, 700 voor Figtree)

### Don'ts

- ❌ Gebruik geen andere fonts naast Figtree en IBM Plex Mono
- ❌ Geen italics voor nadruk — gebruik gewicht of kleur
- ❌ Geen letterspacing < -0.02em of > 0.05em

---

## Toepassing

### Web-apps

Apps consumeren het thema via de semantische token-laag, niet via hardcoded hex-waardes.

```css
.button-primary {
  background: var(--conduction-color-brand-primary);
  color:      var(--conduction-color-text-inverse);
  font-family: var(--conduction-typography-font-family-body);
}
```

### Nextcloud-integraties

Conduction-apps die binnen Nextcloud draaien respecteren waar mogelijk het Nextcloud-thema, maar eigen app-chrome (icon-strip, modals, hero's) gebruikt de Conduction-tokens. Zie per app de NL Design-integratie.

### Documentatie

De Docusaurus-website in [`website/`](./website/) wordt in een vervolg-PR gemigreerd naar het `conduction-2026` thema.

### Presentaties en offertes

- Default template: witte achtergrond, kobaltblauwe koppen, oranje voor 1 accent per slide
- Nooit meer dan 2 accentkleuren op dezelfde slide
- Het avatar altijd in de bovenhoek — links of rechts, consistent binnen het document

---

## Voor bijdragers

Wijzigingen aan het merk raken alle Conduction-apps. Volg:

1. Open een issue met voorstel + rationale
2. Feature-branch `feature/brand-<onderwerp>` vanaf `main`
3. Update bij wijzigingen in kleur/typografie altijd tegelijk: [`brand/tokens.json`](./brand/tokens.json), dit bestand, en [`DESIGN.md`](./DESIGN.md)
4. PR naar `main` met voorbeelden (screenshots) van het effect

Zie [CONTRIBUTING.md](./CONTRIBUTING.md) voor de algemene bijdrage-flow.
