# Conduction Brand Guide

Dit document beschrijft de Conduction huisstijl: wie we zijn, hoe we eruitzien, en hoe je het merk consistent toepast over al onze apps, documentatie en communicatie.

Voor de **rationale** achter onze keuzes: zie [DESIGN.md](./DESIGN.md).
Voor **machine-leesbare tokens**: zie [`brand/tokens.json`](./brand/tokens.json).

---

## Wie we zijn

Conduction is een **Nederlands open-source-productbedrijf**. We bouwen een ecosysteem van samenwerkende Nextcloud-apps. Onze identiteit leunt bewust op Nederlandse kernwaardes:

- **Trots Nederlands.** We ontwerpen vanuit Nederlandse standaarden (NL Design System, Common Ground, API-principes) en dragen dat uit.
- **Innovatief.** We lopen voorop in open source, API-first architectuur, en federatieve datamodellen.
- **Handelsgedreven.** Pragmatisch, doelgericht, resultaatgericht. Oplossingen die werken, niet vertoningen.
- **Penny-wise.** Open source, hergebruik, zuinig met publieke middelen — dezelfde discipline die onze software kenmerkt.
- **Betrouwbaar.** Stabiel, transparant, voorspelbaar. De dieper-blauwe huisstijl onderstreept dat.

## Wat we bouwen — een app-ecosysteem, geen consultancy

Ons model verschuift. Historisch kwam ons werk voort uit *projecten, training en advies*: opdrachten waarin een klant ons inhuurde om iets te bouwen, implementeren of begeleiden. Dat bestaat nog, maar is niet meer waar Conduction om draait.

**Conduction is een productbedrijf.** We bouwen een **ecosysteem van samenwerkende Nextcloud-apps** — OpenRegister, OpenCatalogi, OpenConnector, DocuDesk, MyDash, en meer. Onze klanten kunnen ons gebruiken **zonder ons te hoeven spreken**: ze downloaden de apps uit de Nextcloud app store, installeren, en zijn klaar. Dat is de kern van wat we nu zijn. Alle apps zijn en blijven **altijd gratis en open source** — geen Community/Enterprise-split, geen feature-gating, geen "Pro"-tier.

We verdienen ons brood via twee ondersteunende lagen rondom het ecosysteem:

- **SLA (Service Level Agreement).** Optionele zekerheid-laag bovenop de gratis software: helpdesk-ondersteuning en proactieve begeleiding op basis van telemetry. Klanten krijgen hun SLA via twee paden — via hun eigen Nextcloud-leverancier (voor managed-Nextcloud-gebruikers, met één contract en één factuur), of rechtstreeks via een formulier in de admin-instellingen van de app zelf (voor self-managed Nextcloud). De SLA is *altijd optioneel* en blokkeert geen enkele feature.
- **Services.** Projectmatige activiteiten: implementatie-begeleiding, training, maatwerk-ontwikkeling, advies. Voor klanten met een specifieke behoefte die méér vraagt dan zelfstandig installeren + reactieve support.

Beide zijn **secundair**, niet leading. Alle merkcommunicatie (website, drukwerk, presentaties) leidt met de apps en het ecosysteem; SLA en Services worden discreet vermeld voor wie er specifiek naar zoekt — nooit als verplichte funnel of upgrade-druk.

## Voor wie we bouwen

Onze doelgroep is in transitie:

- **Primair: MKB.** Ons toekomstbeeld. Kleine en middelgrote organisaties die open-source-oplossingen willen gebruiken zonder dure integrator-trajecten. Directe taal, concreet resultaat, zelf installeren.
- **Secundair: Overheid.** Het merendeel van onze **huidige klanten** is nog overheid (gemeenten, samenwerkingsverbanden). We dragen ze niet weg — ze blijven welkom — maar ons zwaartepunt schuift.
- **Tertiair: Ontwikkelaars en integrators.** De open-source-community die bijdraagt aan onze apps, forks maakt, of ze integreert in eigen stacks.

We zijn eerlijk over waar we staan: overheid *is* nog de meerderheid, MKB *is* het doel. De communicatie en het product laten die richting zien zonder de huidige klantenbasis te verloochenen.

## Apps & Solutions — onze terminologie

Dit onderscheid is geldig voor *alle* Conduction-communicatie (website, marketing, sales, documentatie, support), niet alleen voor de website:

- **App** = een stuk software dat we bouwen en uitleveren. Concrete, installeerbare producten. Voorbeeld: *OpenCatalogi*, *OpenRegister*, *DocuDesk*.
- **Solution** = wat een klant ermee kan bereiken. Een oplossing voor een concreet probleem. Voorbeeld: *WOO-compliance*, *organisatieregister*, *zaakafhandeling*.

De relatie tussen beide:

- Eén **app** kan aan meerdere **solutions** bijdragen (OpenCatalogi is relevant voor WOO-compliance én voor softwarecatalogi)
- Eén **solution** vraagt vaak meerdere **apps** (WOO-compliance combineert OpenCatalogi + OpenConnector + DocuDesk)
- We communiceren vanuit beide kanten: apps voor wie weet welk product hij zoekt; solutions voor wie een probleem heeft en de weg naar de juiste app-stack nodig heeft

Consequentie voor taalgebruik: vermijd zinsconstructies als *"onze WOO-app"* (er is geen WOO-app, WOO is een solution die meerdere apps vraagt). Zeg in plaats daarvan *"onze WOO-solution, gebouwd op OpenCatalogi en OpenConnector"*.

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
| **Secondary** | KNVB-oranje | `#F36C21` | 243, 108, 33 | Accenten, highlights, hover — spaarzaam |
| **Tertiary** | Helder vermiljoen | `#AE1C28` | 173, 28, 40 | Zeer spaarzaam — attentie, error-state |
| **Background** | Wit | `#FFFFFF` | 255, 255, 255 | Default achtergrond |

### Waarom deze drie?

- **Kobaltblauw** is officieel de blauwtint van de Nederlandse vlag. Donkerder dan onze oude lichtblauw, straalt betrouwbaarheid en stabiliteit uit.
- **KNVB-oranje** is het meest universeel herkenbare "Nederlands oranje" — het oranje van het nationale elftal. Warm, toegankelijk, emotioneel geladen. Expliciet *niet* het Rijkshuisstijl-oranje (`#E17000`), en ook niet de letterlijke wimpel-tint (`#FF7F00`): de KNVB-variant pairt zachter met cobalt en signaleert "Nederlands maar niet overheid, trots maar niet stoffig".
- **Vermiljoen** is de officiële rode vlagkleur. Spaarzaam in te zetten voor attentie en error-states.

Zie [DESIGN.md](./DESIGN.md#waarom-knvb-oranje-f36c21-als-secundair) voor de volledige afweging, inclusief vergelijking met Rabobank, ING en Rijkshuisstijl.

### Wat oranje betekent voor Conduction

KNVB-oranje is onze **accent**-kleur, niet onze hoofdkleur. Het staat symbool voor:

- **Warmte en toegankelijkheid** — we zijn een bedrijf van mensen, niet een monolithisch instituut
- **Nederlandse identiteit op mass-appeal niveau** — iedereen herkent "Oranje" (elftal, Koningsdag, Oranjegekte), zonder overheidsverwijzing
- **Pragmatisch optimisme** — energie, actie, "we bouwen dingen die werken"
- **Focus** — in UI trekt oranje het oog naar één ding tegelijk

Oranje is daarmee het tegengewicht van cobalt: cobalt draagt structuur en vertrouwen, oranje draagt beweging en menselijkheid.

### Proportie

Richtlijn voor balans in vlakverdeling:

- **70%** wit (achtergrond, ademruimte)
- **20%** kobaltblauw (merk, structuur, tekst)
- **8%** oranje (accent, hover, highlight)
- **2%** vermiljoen (uiterst spaarzaam)

Oranje en vermiljoen zijn **krachtige** kleuren — gebruik ze als bijspeler, niet als hoofdrolspeler.

### Subtiel gebruik van oranje — concreet

Oranje werkt wanneer het **één ding** accentueert. Plaatsen waar het goed past:

- **Focus rings** rond formulier-inputs en buttons
- **Hover states** voor links en interactieve elementen (link default = cobalt, hover = oranje)
- **Badges** voor "nieuw", "beta", "featured" (max. één per scherm)
- **Iconografie-accenten** — een icoon in cobalt met één oranje detail, niet een volledig oranje icoon
- **Onderstrepingen** of markers bij headings van de kern-boodschap (één per pagina)
- **Call-to-action-randjes** — primary button blijft cobalt met witte tekst; oranje kan als border, shadow of micro-accent
- **Illustraties** — als highlight-kleur binnen een cobalt-dominant illustratiestijl
- **Grafiek-hoogtepunten** — één datapunt of lijn in oranje, rest in cobalt-tinten

Plaatsen waar oranje **niet** werkt:

- Grote vlakken (hero-achtergrond, sidebar-fill, card-background)
- Primary fill van een knop (oranje op wit kan druk ogen; gebruik cobalt-fill met wit)
- Body-tekst (te weinig contrast op wit)
- Meer dan één accent per scherm (oranje werkt door spaarzaamheid; twee oranje elementen concurreren)

### Do's

- ✅ Gebruik cobalt voor structuur en primaire acties
- ✅ Gebruik oranje voor attentie zonder alarm (hover, nieuwe badge, focus ring)
- ✅ Gebruik vermiljoen alléén voor echte attentie (error, destructieve actie)
- ✅ Max. één oranje accent per scherm — spaarzaamheid is de bron van zijn kracht

### Don'ts

- ❌ Meng oranje en rood nooit in hetzelfde oppervlak
- ❌ Gebruik geen oranje voor grote vlakken (hero-achtergrond, sidebar)
- ❌ Maak geen primary buttons met oranje fill — dat behoort cobalt toe
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
