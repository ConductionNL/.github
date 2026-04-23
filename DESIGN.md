# Conduction Design Rationale

Dit document legt vast **waarom** we de ontwerpkeuzes hebben gemaakt die in [BRAND.md](./BRAND.md) staan en in [`brand/tokens.json`](./brand/tokens.json) zijn vastgelegd. BRAND.md is het "wat" en "hoe"; dit is het "waarom".

> **Thema:** `theme-conduction-2026`
> **Status:** Scope A (kleur + typografie). Spacing, radii, shadows, motion en componenttokens volgen in latere ronden.
> **Transitie:** Harde switch. Apps stappen over; er is geen parallel legacy-thema.

---

## Uitgangspunt: een Conduction-thema, dat toevallig op NLDS leunt

We kiezen voor een **Conduction-eigen naamruimte** (`theme.conduction-2026.*`) boven directe NL Design System-namespaces. Redenen:

1. **Conduction is geen overheid.** Onze apps worden gebruikt door overheden, maar we zijn een bedrijf met een eigen identiteit. Die moet herkenbaar blijven.
2. **Vrijheid waar nodig.** NLDS is sterk op gemeentelijke/rijks-design, maar heeft geen sluitende tokens voor alle use-cases van een productbedrijf (bv. een accentkleur die bewust afwijkt van de Rijkshuisstijl).
3. **Interop waar mogelijk.** Voor overlappende tokens volgen we NLDS conventies en waardes, zodat NLDS-componenten drop-in werken in Conduction-apps. Zie mapping in [`brand/README.md`](./brand/README.md).

**Concreet:** een NLDS-knop die `--nl-color-primary` verwacht krijgt die via een mapping-laag in elke app (of de primary is direct gelijk aan NLDS-primary bij de apps die dat volgen).

---

## Kleuren

### Waarom kobaltblauw `#21468B`?

Onze oude merkkleur was een lichter, frisser blauw (`#4376FC`-achtig, zie [de legacy avatar](./brand/assets/avatar-conduction-on-white.svg) vóór de recolor). Dat straalde "tech / modern" uit, maar te weinig **gewicht**. Een productbedrijf dat met overheden werkt, moet vertrouwen uitstralen.

Kobaltblauw `#21468B`:

- **Is officieel de blauwtint van de Nederlandse vlag.** Dat past bij onze positionering: een trots Nederlands open-source-bedrijf.
- **Is donker.** Donkerdere blauwen worden als betrouwbaarder, stabieler, serieuzer ervaren — precies wat we willen uitdragen.
- **Heeft uitstekend contrast** op wit (≈ 9.2:1, WCAG AAA). We kunnen cobalt dus óók voor body-tekst gebruiken, wat het merk consistenter maakt.

**Afgewezen alternatieven:**
- *NLDS utrecht-blauw (`#154273`)*: ook donker, ook mooi — maar niet de officiële vlagkleur, dus geen Nederlandse associatie.
- *Midnight / navy (`#0C2D48`)*: te donker, gaat richting zwart, verliest kleuridentiteit.
- *Huidige lichtblauw behouden met extra gewicht via typografie*: overwogen, maar onvoldoende signaal van de gewenste richting.

### Waarom KNVB-oranje `#F36C21` als secundair?

We hebben drie oranjetinten overwogen: wimpel-oranje `#FF7F00` (de letterlijke wimpel die boven de Nederlandse vlag wappert bij staatsaangelegenheden), Rijkshuisstijl-oranje `#E17000` (de accent­kleur van de Nederlandse overheid), en KNVB-oranje `#F36C21` (het oranje van het nationale elftal en bij uitbreiding de "Oranje"-beleving).

**Rijkshuisstijl-oranje valt meteen af.** Die kleur is geassocieerd met "de overheid", en onze apps worden weliswaar *door* overheden gebruikt, maar Conduction is een bedrijf. Verwarring met een overheidsdienst is positionerings-schadelijk.

Tussen wimpel en KNVB gaat het om karakter en harmonie met cobalt:

| Eigenschap | Wimpel `#FF7F00` | KNVB `#F36C21` |
|---|---|---|
| Hue | 30° (puur oranje) | 22° (licht rood-leanend) |
| Saturatie | 100% | 90% |
| Luminantie (L in HSL) | 50% | 54% |
| WCAG-contrast op cobalt | 3.58:1 | 3.01:1 (net 3:1-grens voor UI-accents) |
| Pairing met cobalt | Letterlijk complement — kan "buzzen" | Zachter, iets warmer, minder vibratie |
| Signaal | Officieel, institutioneel, "vlag-poster" | Warm, mass-appeal, "Oranjegekte" |
| Culturele lading | Wimpel = staatsaangelegenheden, ceremonieel | Elftal = toegankelijke patriottisme |

KNVB wint op drie fronten:

1. **Zachtere harmonie met cobalt.** De lichte rood-lean en iets lagere saturatie geven een volwassener, minder hard-contrasterende pairing. Minder "posterkleur", meer "professioneel bedrijf met Nederlandse identiteit".
2. **Emotionele resonantie zonder Rijks-associatie.** KNVB-oranje is het meest universeel herkenbare "Nederlands oranje" — toegankelijker dan wimpel — maar zonder de overheidslading van rijksoranje.
3. **Past bij "innovatief / handelsgedreven / menselijk".** Wimpel leunt naar formeel; KNVB leunt naar energiek-toegankelijk. De briefing vraagt om het tweede.

Prijs die we betalen: ~0.57 contrast-punten minder op cobalt (3.01 vs 3.58). Voor icoon- en accent-gebruik is 3:1 voldoende (WCAG AA voor non-text). Voor grotere oranje elementen waarin leesbaarheid ertoe doet, gebruiken we oranje *op wit* (contrast 4.96:1, AAA voor grote tekst), niet *op cobalt*.

### Wat oranje betekent voor Conduction

KNVB-oranje is onze **accent**-kleur, niet onze hoofdkleur. Semantisch staat het voor:

- **Warmte en toegankelijkheid** — we zijn een bedrijf van mensen, niet een monolithisch instituut
- **Nederlandse identiteit op mass-appeal niveau** — "Oranje" (elftal, Koningsdag, Oranjegekte) herkent iedereen, zonder overheidsverwijzing
- **Pragmatisch optimisme** — energie, actie, "we bouwen dingen die werken"
- **Aandacht-focus** — in UI trekt oranje het oog naar één ding tegelijk

Oranje is daarmee het **tegengewicht** van cobalt: cobalt draagt structuur en vertrouwen, oranje draagt beweging en menselijkheid. Samen zeggen ze: *stabiel én benaderbaar*.

### Subtiel gebruik: de 8%-regel

Proportioneel houden we oranje op **maximaal ~8%** van een gegeven oppervlak. Dat is geen toevallige grens — het is de hoeveelheid waarbij accentkleur als accent ervaren wordt en niet als secondary brand-kleur. Boven de 10% begint oranje te concurreren met cobalt en verliest het zijn attention-werking.

Concrete plaatsen waar oranje werkt (zie [BRAND.md](./BRAND.md#subtiel-gebruik-van-oranje--concreet) voor de volledige lijst):

- Focus rings, hover states, "nieuw"-badges
- Één datapunt in een grafiek, één icoon-detail, één highlight-woord
- Randen, schaduwen, micro-accenten op cobalt-dominante elementen
- Illustratie-highlights binnen een cobalt-palet

Waar oranje uitdrukkelijk **niet** werkt:

- Grote vlakken (hero-backgrounds, sidebar-fills, card-backgrounds)
- Primary button fill (dat is cobalt-gebied)
- Body-tekst op wit (wel voldoende contrast, maar te druk)
- Meer dan één accent per scherm

### Overwogen kleurcombinaties — hoe staan wij tussen andere Nederlandse identiteiten?

Cobalt + KNVB-oranje is geen onontgonnen terrein; meerdere Nederlandse merken combineren donkerblauw met een oranje-accent. De vraag is of onze combinatie voldoende **onderscheidend** is.

| Identiteit | Blauw | Oranje | Karakter | Onderscheid t.o.v. Conduction 2026 |
|---|---|---|---|---|
| **Conduction 2026** (voorstel) | `#21468B` kobalt (L=34%) | `#F36C21` KNVB (H=22°) | Warm-professioneel, Nederlands-toegankelijk | — |
| **Rabobank** | `#000066` donker navy (L=20%) | `#FF6600` | Conservatief, bancair, traditioneel | Rabo's navy is véél donkerder (bijna zwart-blauw); hun oranje is feller en meer pure 30°. Bank-feel, niet product-feel. |
| **ING** | `#000066` donker navy (L=20%) | `#FF6200` | Modern bancair, fintech | Vrijwel identiek aan Rabobank qua blauw; iets roodder oranje. Blauw veel donkerder dan cobalt. |
| **Rijkshuisstijl** | `#154273` rijksblauw (L=27%) | `#E17000` rijksoranje (L=44%) | Formeel, overheid, institutioneel | Blauw iets donkerder dan cobalt; oranje duidelijk donkerder en bruiner. Overheids­associatie uitgesloten voor ons. |
| **KNVB / Oranje-elftal** | `#19284B` navy (L=20%) | `#F36C21` KNVB | Sport, nationale trots | Ons blauw is lichter en herkenbaarder als vlag-cobalt; oranje is identiek. |
| **Nederlandse vlag (officieel)** | `#21468B` kobalt | *(geen oranje; rood `#AE1C28`)* | Staatsembleem | Wij gebruiken exact hetzelfde blauw; oranje is voor ons secundair. |

**Conclusie uit de tabel:**

- Banken (Rabobank, ING) claimen het **donkerste** navy-oranje register. Hun navy (`#000066`) is ruwweg 14 L-punten donkerder dan onze cobalt — dat is een zichtbaar andere categorie. Onze cobalt ademt meer "daglicht" en ligt dichter bij de vlagtint.
- Rijkshuisstijl zit ertussen qua blauw maar kiest een bruiner oranje. Wij vermijden hun oranje.
- KNVB gebruikt ons exacte oranje, maar met donkerder navy. Het elftal-combo is niet verwarrend met ons, maar "borrowt" wel dezelfde Nederlandse warmte — dat is een feature, geen bug.
- Onze pairing (lichter cobalt + warmer oranje) zit in een "gat" tussen banken (te donker, te formeel) en overheid (te bruin, te institutioneel). Dat gat is precies waar een open-source-productbedrijf thuishoort: Nederlands, professioneel, maar niet corporate-stoffig of staatsdienst-streng.

Als in de toekomst een concurrent in hetzelfde register komt, kunnen we onderscheiden via **toepassing en proportie** (de 8%-regel, hexagon-wrapper, typografie) — het is niet alleen het kleurenpalet dat ons kenbaar maakt.

### Waarom vermiljoen `#AE1C28` als tertiair?

Helder vermiljoen is de officiële rode vlagkleur. We nemen het op omdat:

- Het compleet maakt wat Nederland is: rood-wit-blauw
- Het een natuurlijke kandidaat is voor error-states en destructieve acties
- Een apart rood voor status los houden van branding voorkomt inconsistentie (anders krijg je "Tailwind red-500" in de ene app en "Bootstrap danger" in de andere)

Vermiljoen is **nog spaarzamer** dan oranje (~2%). Overmatig rood voelt alarmerend.

### Waarom geen neutrale grijzen in scope A?

Scope A is bewust minimaal. Voor body-tekst gebruiken we kobalt op wit (contrast is ruim voldoende). Voor muted/secondary tekst, borders, subtle backgrounds hebben we grijzen nodig — dat komt in **scope B**. Voor nu kunnen apps tijdelijk hun eigen neutrale grijs gebruiken; we standaardiseren dat zodra meerdere apps ermee werken.

---

## Typografie

### Waarom Figtree?

Briefing: **voller, ronder, rustiger, professioneler** dan de huidige typografie (die "te hard" aanvoelt).

Kandidaten vergeleken:

| Font | Vol/rond | Rustig | Professioneel | Oordeel |
|---|---|---|---|---|
| DM Sans | ✅✅ | ✅✅ | ✅ | Zeer goede optie — iets neutraler |
| Figtree | ✅✅ | ✅✅ | ✅✅ | **Gekozen** — warmte + professionaliteit |
| Manrope | ✅ | ✅ | ✅✅ | Koeler, tech-signaal sterker |
| Fira Sans | ✅ | ✅ | ✅✅ | Humanist maar scherper |
| Public Sans | — | ✅ | ✅✅ | Neutraal, mist karakter |
| Nunito | ✅✅ | ✅✅ | — | Te speels voor B2B/gov |

Figtree won omdat het:

- **Ronde contraformen** heeft (zacht, vriendelijk) zonder speels te worden
- **Hoge x-height** heeft (goed leesbaar op schermen)
- **Meerdere gewichten** (300–900) ondersteunt, genoeg voor een complete type-ramp
- **OFL-licensed** is en gratis via Google Fonts beschikbaar
- **In productie bewezen** — gebruikt door bv. Vercel-ecosystem, Linear-achtige tools

### Waarom IBM Plex Mono voor code?

- Warmer in vorm dan JetBrains Mono (past beter naast Figtree)
- Rustig en zeer leesbaar — geen sterke stylistische accenten
- OFL, brede taalondersteuning
- Conductie-apps zijn geen pure developer tools — een "te technische" mono (JetBrains Mono, Fira Code met ligaturen) trekt te veel aandacht

Als in de toekomst een app bewust developer-facing wordt (API-console, debugger), kan die lokaal overstappen op JetBrains Mono — maar de default blijft IBM Plex Mono.

### Waarom geen aparte display-font voor koppen?

Overwogen: DM Serif Display / Fraunces / Playfair als display-accent. Afgewezen omdat:

- Serif koppen boven sans body voelt in B2B-context al snel "uitgeversachtig" of magazine-stijl, niet zakelijk
- Tweede font = extra bandwidth + extra complexiteit voor consumenten van de tokens
- Figtree in 700 weight heeft genoeg gewicht en karakter voor koppen

Als we in de toekomst één display-weight willen toevoegen voor hero's (bv. Figtree 900), doen we dat per app op basis van noodzaak — niet globaal.

---

## Logo

### Waarom de hexagon-wrapper behouden?

De zeshoek is in alle huidige Conduction-apps het herkenbaar omkapsel. Hem behouden bij de stijlvernieuwing:

- **Bewaart institutioneel geheugen** — gebruikers die Conduction-apps kennen, herkennen ons meteen
- **Schaalt over het portfolio** — elk app-icon past binnen dezelfde vorm, maakt portfolio-pagina's rustig
- **Heeft geen gevestigde associatie** in overheidsland — geen botsing met Rijkshuisstijl-iconografie

### Waarom twee logo-varianten (op wit, op blauw)?

- **Op wit** is de default — documenten, lichte UI, website
- **Op blauw** is nodig voor hero-secties, social-media avatars met donkere achtergrond, en Nextcloud dark-mode
- Beide staan in [`brand/assets/`](./brand/assets/). Plus een transparante variant voor gevallen waar de achtergrond bekend/variabel is.

Bronbestanden:

- [Kobalt op wit](./brand/assets/avatar-conduction-on-white.svg) — default
- [Wit op kobalt](./brand/assets/avatar-conduction-on-blue.svg) — inverse
- [Transparant](./brand/assets/avatar-conduction.svg) — flexibel

### Waarom niet een volledig nieuw logo?

De kleurvernieuwing is al een significant signaal. Een nieuwe vorm bovenop nieuwe kleuren zou:

- Continuïteit breken (bestaande gebruikers heroriënteren zich onnodig)
- Veel meer visuele inventaris raken (app-icons, social, drukwerk, merchandise)
- De boodschap verwateren — we willen zeggen "nieuwe, serieuzere kleur", niet "nieuw bedrijf"

De zeshoek blijft; de kleur wordt volwassener. Dat is de boodschap.

---

## Implementatie-aanpak

### Harde switch, geen parallel thema

Overwogen werd: twee thema's naast elkaar (`theme-legacy`, `theme-conduction-2026`) waar apps individueel overstappen. Afgewezen:

- **Twee waarheden meedragen is duur.** Elke kleur/typografie-wijziging moet in beide.
- **Apps zouden achterblijven.** Zonder deadline wordt legacy nooit verlaten.
- **De nieuwe stijl is het gewenste eindbeeld.** Een harde switch signaleert commitment.

De migratie gebeurt per app in eigen tempo, maar alle apps consumeren **hetzelfde** `conduction-2026` thema. Er is geen rollback-thema.

### Waarom DTCG-formaat?

W3C [Design Tokens Community Group](https://design-tokens.github.io/community-group/format/) is het opkomende standaardformaat:

- **Tool-agnostisch** — Style Dictionary, Tokens Studio, Figma, Supernova ondersteunen het (of zijn bezig ermee)
- **Toekomstbestendig** — we zitten niet vast aan één tooling
- **Zelf-documenterend** — `$description` velden leven naast waardes
- **Referentie-resolutie** — `{color.primitive.blue.cobalt}` ketent primitief → thema

Alternatief was Style Dictionary v3 formaat (zonder `$`), maar DTCG is breder en SD v4 gaat er naartoe. Geen reden voor legacy format.

### Waarom scope A eerst (kleur + typografie)?

- **80% van de merkherkenning** zit in kleur + typografie
- **Snelste time-to-visible-change** — apps kunnen vandaag al migreren zonder op spacing/radii te wachten
- **Beperkt risico** — minder oppervlak om fout te krijgen
- **Leer-iteratie** — uit de eerste migraties leren we wat de volgende scope moet dekken

Spacing/radii/shadows (scope B) en componenttokens (scope C) volgen op basis van daadwerkelijke vraag uit app-migraties, niet op speculatie.

---

## Rollout — welke oppervlakken, in welke volgorde

Het thema landt niet in één klap overal. Drie soorten oppervlakken met elk een eigen prioriteit en complexiteit:

| Oppervlak | Doel | Codebase | Prioriteit |
|---|---|---|---|
| `www.conduction.nl` | Marketing, wervend, eerste indruk | Aparte codebase (stack nader te bepalen) | **Hoog** — grootste merkimpact richting (potentiële) klanten |
| `docs.conduction.nl` | Technische documentatie voor integrators | Docusaurus in [`.github/website/`](./website/) | **Middel** — goede eerste testcase voor de tokens |
| App-UI's (OpenRegister, OpenCatalogi, …) | Productgebruik | Per app-repo | **Middel-hoog** — dagelijks zichtbaar voor eindgebruikers |

### Waarom deze volgorde

- **`www.conduction.nl` eerst** omdat merk-uitstraling het grootste effect heeft op prospects die ons nog niet kennen. De donkerdere kobalt plus KNVB-oranje vertelt een ander verhaal over wie we zijn — die boodschap landt het eerst op de marketingsite.
- **`docs.conduction.nl` als parallelle technische proef.** Technisch laagdrempelig (één Docusaurus `custom.css` vervangen, fonts toevoegen via `stylesheets` in `docusaurus.config.js`) en laag visueel risico — docs mogen iteratief. Het legt bovendien bloot welke scope-B tokens (spacing, radii, shadows) als eerste nodig zijn zodra een echte site ze consumeert.
- **Apps per stuk, op eigen tempo.** De harde switch betreft het *thema-contract* (`theme-conduction-2026`), niet een gedeelde deadline voor alle apps. Elke app-repo landt zijn eigen migratie-PR.

### De "docs-first vs marketing-first"-afweging

Vanuit techniek is docs-first logisch (kleiner, overzichtelijker, snel klaar). Vanuit positionering is marketing-first logisch (merkimpact). We kiezen **marketing-first**, met docs als parallelle technische proef.

Als de marketing-site echter op een platform draait dat moeilijk tokens consumeert (bv. Webflow of een WordPress-theme zonder build-pipeline), draait de volgorde om — dan is `docs.conduction.nl` het eerste formele bewijs van het thema in gebruik, en landt de marketingsite via export van dezelfde waardes.

### Wat telt als "gemigreerd"?

Een oppervlak is pas gemigreerd wanneer:

1. Alle merkkleuren via `theme.conduction-2026.color.brand.*` worden geconsumeerd (geen hardcoded hex)
2. Typografie via de `theme.conduction-2026.typography.font-family.*` tokens loopt
3. Het avatar in de juiste variant (op-wit of op-blauw) gebruikt wordt
4. Er geen `#4376FC` of andere legacy-blauwtint meer in het oppervlak voorkomt

Tot die tijd is het oppervlak "in transitie".

---

## Open vragen / toekomstige beslissingen

Deze noteren we alvast, maar lossen we niet in deze ronde op:

- **Dark mode** — aparte thema-variant of automatische inversie op basis van tokens? Voor scope B.
- **Accessibility-varianten** — high-contrast mode, reduced-motion? Voor scope B/C.
- **App-specifieke accent-kleuren** — mag een Conduction-app zijn eigen "OpenCatalogi-blauw" hebben, of alleen binnen het merk-palet blijven? Nu: alleen binnen het merk-palet. Heroverwegen als dat knelt.
- **NLDS versie-pinning** — als NLDS majors uitbrengt die tokens hernoemen, volgen we automatisch of gecontroleerd? Voor later.

---

## Wijzigingshistorie

| Datum | Wijziging | Besluit door |
|---|---|---|
| 2026-04-23 | Introductie `theme-conduction-2026`: kobalt + KNVB-oranje + vermiljoen, Figtree + IBM Plex Mono, zeshoek-wrapper behouden. Wimpel-oranje (`#FF7F00`) en Rijkshuisstijl-oranje (`#E17000`) overwogen en afgewezen; KNVB gekozen om warmere harmonie met cobalt en mass-appeal "Oranje"-associatie zonder overheidslading. | Brand-initiatief |
