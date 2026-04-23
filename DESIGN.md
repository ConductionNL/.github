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

### Waarom windmolen-oranje `#FF7F00` als secundair, en niet rijkshuisstijl-oranje?

Rijkshuisstijl-oranje (`#E17000`) is de accentkleur van de Nederlandse overheid. Als wij dat overnemen, worden we visueel verward met een overheidsdienst — ongewenst. Windmolen-oranje (`#FF7F00`) is:

- Iets feller, duidelijk anders dan rijksoranje
- Associatief met Nederland (Oranje-boven, windmolens) zonder de Rijkshuisstijl-implicatie
- Een heldere accentkleur die op wit goed opvalt maar niet agressief is

Oranje blijft beperkt tot ~8% van een oppervlak. Het is **accent**, geen hoofdkleur.

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
| 2026-04-23 | Introductie `theme-conduction-2026`: kobalt + windmolen + vermiljoen, Figtree + IBM Plex Mono, zeshoek-wrapper behouden | Brand-initiatief |
