# Conduction Support-model — hoe ons verdienmodel werkt

Dit document beschrijft hoe Conduction geld verdient: niet door de software achter een paywall te zetten, maar door organisaties die extra zekerheid willen een **Support-abonnement** aan te bieden. Voor het website-ontwerp is dit essentieel omdat het bepaalt welke CTA's, formulieren en pagina-structuren we wel/niet bouwen.

> **Naamgeving:** we gebruiken op de website en in klant-communicatie het woord **"Support"**, niet "SLA". SLA is een technische term voor het onderliggende contract (het *agreement* waarin de *service levels* vastliggen). Klanten zoeken op "support", niet op "SLA". Binnen dit document en in contracten mag "SLA" gewoon worden gebruikt als precieze term.

**Kernpunt:** de software is en blijft **altijd gratis en altijd open source**. Geen Community vs Enterprise, geen feature-gating, geen "Pro"-tier. Support is een **zekerheidslaag** *bovenop* de gratis software, niet een voorwaarde om de software te gebruiken.

## Wat zit er in Conduction Support?

Twee concrete componenten. Alles wat we beloven staat in deze lijst — als het er niet in staat, maakt het geen onderdeel uit van Support.

### 1. Helpdesk-ondersteuning

Reactieve support voor vragen, bugs en problemen die de klant zelf tegenkomt. Kanaal en reactietijden worden in het contract vastgelegd (typisch e-mail + ticketsysteem, werkdagen, response binnen X uur afhankelijk van tier).

### 2. Proactieve ondersteuning via telemetry

Met toestemming van de klant kijken we mee op telemetry-data van hun apps — systemen, performance, fout-patronen. We zien problemen vaak vóórdat de klant erover belt. Voorbeelden:

- Foutpatronen die zich opstapelen maar nog niet hebben geëscaleerd
- Database-groei die binnen 3 maanden tegen een drempel aanloopt
- Integraties die falen zonder dat het operationeel nog merkbaar is
- Upgrades die breken bij bekende app-combinaties

We bellen of mailen de klant dan actief: *"Hé, we zien X, we raden aan Y te doen, wil je dat we meekijken?"*

Geen Support-abonnement? Dan zien we die telemetry niet (of niet-gekoppeld) en draait de klant op zichzelf.

### Wat géén onderdeel is van Support

Expliciet vermelden om verwachtingen te managen:

- **Geen 24/7-dekking** als dat niet in het contract staat (we zijn geen NOC)
- **Geen maatwerk-development** — dat is een Service-traject, geen Support-onderdeel
- **Geen training** — ook Services, niet Support
- **Geen implementatie-begeleiding** — Services
- **Geen hosting** — wij zijn geen hosting-partij; zie de twee paden hieronder

### Support vs Services — het onderscheid

Beide zijn betaalde lagen rondom onze gratis apps, maar structureel anders:

| | Support | Services |
|---|---|---|
| **Wat** | Doorlopende ondersteuning op geïnstalleerde apps | Projectmatige activiteiten |
| **Wanneer relevant** | Je draait de apps en wilt zekerheid | Je hebt een specifieke behoefte die vraagt om handjes of expertise |
| **Concreet** | Helpdesk + proactieve telemetry-monitoring | Maatwerk-ontwikkeling, training, implementatie-begeleiding |
| **Verdienmodel** | Abonnement (per app × per user × per jaar) | Projectprijs of uurtarief |
| **Contract** | Doorlopend | Per project |
| **Website-plek** | Eigen pagina met tiers en pricing | Discrete footer-pagina |

Een klant kan beide afnemen, één, of geen. De apps werken altijd, ongeacht.

## De twee Support-paden

Het verschil tussen onze twee Support-paden is **wie de aanspreekpartij is en wie de factuur stuurt**. De inhoud van Support zelf is identiek.

### Pad 1 — Support via een Nextcloud-leverancier (gangbaarste)

**Wie herkent deze situatie:** organisaties die hun Nextcloud-omgeving *niet zelf beheren* maar afnemen bij een managed Nextcloud-partner (officiële Nextcloud-leverancier, een hosting-partij of reseller).

**Flow:**

1. Klant heeft al een Nextcloud-contract bij een leverancier
2. Klant wil Conduction-apps gebruiken mét Support-zekerheid
3. Klant spreekt dat af via hun eigen leverancier — één aanspreekpartij, geen verandering in leveranciers-relatie
4. Apps worden ofwel door de leverancier geïnstalleerd, ofwel door de klant zelf uit de Nextcloud app store
5. Conduction en de leverancier regelen het Support-contract onderling via Nextcloud als tussenpartij (officiële Nextcloud-leverancier-route)
6. Conduction factureert de Support-kosten via Nextcloud aan de leverancier
7. De leverancier zet die kosten door op zijn eigen factuur aan de klant

**Voordeel voor de klant:**

- Eén aanspreekpartij (hun Nextcloud-leverancier)
- Eén contract (uitgebreid met Support, niet een nieuw afzonderlijk contract met Conduction)
- Eén factuur (van hun Nextcloud-leverancier, die Conduction's Support-kosten heeft doorgezet)
- Geen aparte relatie met Conduction opbouwen; de leverancier staat ertussen

**Implicatie voor de website:**

- Dit pad vereist **geen aankoop-flow op onze site**. De klant regelt dit met zijn leverancier, niet rechtstreeks met ons.
- Wat we wél moeten bieden: een **lijst van Nextcloud-leveranciers** waarmee deze route werkt, of een verwijzing daarnaar.
- CTA: *"Neem contact op met je Nextcloud-leverancier om Conduction-Support af te nemen"*

### Pad 2 — Support rechtstreeks met Conduction (self-managed Nextcloud)

**Wie herkent deze situatie:** organisaties die hun eigen Nextcloud draaien (self-hosted, zonder leverancier, of met een leverancier die geen Conduction-Support aanbiedt), maar toch Support-zekerheid willen.

**Flow:**

1. Klant heeft zelf een Nextcloud draaien — niet-managed, geen officiële Nextcloud-leverancier-relatie voor support
2. Klant downloadt Conduction-apps uit de Nextcloud app store en installeert ze zelf
3. In de app — onder de Admin-settings → [AppName] → Support — vult de klant een formulier in om Support aan te vragen
4. Conduction neemt contact op, stelt een Support-contract op, factureert rechtstreeks aan de klant

**Voordeel voor de klant:**

- Geen afhankelijkheid van een Nextcloud-leverancier
- Directe relatie met de makers van de apps
- Keuze: welke apps onder Support, welke niet

**Implicatie voor de website:**

- Dit pad vereist ook **geen aankoop-flow op onze site** — het Support-formulier zit **in de app zelf**, niet op de website. Dat is een bewuste keuze: je moet de app eerst hebben om Support te willen, dus het formulier hoort bij de app.
- Wat we wél moeten doen op de site: **uitleggen dat pad 2 bestaat**, en dat het formulier "in de admin-instellingen van de app zelf" te vinden is.
- CTA: *"Installeer de app. In de Admin-instellingen vind je het Support-aanvraag-formulier."*

## Pricing — structuur

Conduction Support wordt afgerekend **per app × per gebruiker × per jaar** met twee tiers (Standard en Premium). Dit volgt het patroon dat Nextcloud Enterprise zelf hanteert (`/pricing` op nextcloud.com), maar met aanpassingen voor onze MKB-doelgroep.

> **Benchmark-verwijzing:** Nextcloud rekent €71–205/user/jaar voor hun Files-abonnement, met een minimum van 100 users en tiers Standard/Premium/Ultimate. Zie [`platform-benchmarks.md §Nextcloud pricing`](./platform-benchmarks.md#nextcloud--derde-benchmark-free-core--paid-support) voor de details. Wij zitten structureel lager én met veel lagere user-minimums omdat onze MKB-markt niet begint bij 100 gebruikers.

### Tiers

#### Standard

- **Helpdesk:** e-mail/ticketsysteem, werkdagen (08:00–17:00), responstijd ≤ 2 werkdagen
- **Proactieve ondersteuning:** maandelijks telemetry-rapport met trending issues, aanbevolen acties
- **Update-assistentie:** e-mail-notificaties bij breaking upgrades of security-patches
- **Minimum:** 10 gebruikers per app onder Support

#### Premium

- **Helpdesk:** e-mail + telefoon, werkdagen (08:00–17:00), responstijd ≤ 1 werkdag
- **Proactieve ondersteuning:** real-time monitoring met proactieve alerts; direct contact bij incidenten
- **Update-assistentie:** upgrade-begeleiding per major-release, test-omgeving ondersteuning
- **Minimum:** 25 gebruikers per app onder Support

Beide tiers: **jaarlijks contract**, **ex. BTW**, **bundel-korting** van 20% bij Support op 3+ apps, **maatwerk-tier** (24/7, kortere responstijden) op aanvraag voor grotere organisaties.

### Pricing-tabel per app

> **⚠ Placeholder-waarden.** Onderstaande prijzen zijn **voorlopig** en moeten worden bevestigd vóór publicatie. De structuur (groepering, tier-verhoudingen) kan worden overgenomen; de exacte getallen moet Conduction-leiding vaststellen op basis van gewenste marge, markt-positie en Nextcloud-revenue-share-afspraken.

De 11 core apps zijn gegroepeerd in drie klassen op basis van operationele complexiteit (hoe kritisch een incident is voor de klant, hoeveel support-inzet per klant gemiddeld).

| App | Categorie | Standard | Premium |
|---|---|---|---|
| **OpenRegister** | Foundation | €TBD / user / year | €TBD / user / year |
| **OpenCatalogi** | Foundation | €TBD / user / year | €TBD / user / year |
| **OpenConnector** | Core integratie | €TBD / user / year | €TBD / user / year |
| **DocuDesk** | Core | €TBD / user / year | €TBD / user / year |
| **ZaakAfhandelApp** | Core | €TBD / user / year | €TBD / user / year |
| **Procest** | Core | €TBD / user / year | €TBD / user / year |
| **PipelinQ** | Core | €TBD / user / year | €TBD / user / year |
| **MyDash** | Ondersteunend | €TBD / user / year | €TBD / user / year |
| **SoftwareCatalog** | Ondersteunend | €TBD / user / year | €TBD / user / year |
| **LarpingApp** | Ondersteunend | €TBD / user / year | €TBD / user / year |
| **NL Design** | Ondersteunend | €TBD / user / year | €TBD / user / year |

**Indicatieve range als input voor bevestiging** (niet publiceren zonder bevestiging):

- Foundation-apps: Standard ca. €15–20/user/year, Premium ca. €30–40/user/year
- Core-apps: Standard ca. €10–15/user/year, Premium ca. €20–30/user/year
- Ondersteunend: Standard ca. €5–10/user/year, Premium ca. €10–20/user/year

Rekenvoorbeeld (indicatief, niet-bindend): gemeente met 150 gebruikers die Support Standard wil op OpenRegister + OpenCatalogi + DocuDesk → (150 × €17,50) + (150 × €17,50) + (150 × €12,50) = ~€7.125/jaar, met 20% bundel-korting (3+ apps) = **~€5.700/jaar**. Voor dezelfde gemeente Premium zou ca. €12.000–13.000/jaar zijn.

**Opmerkingen bij de structuur:**

- **Minimum 10 users per app** (Standard) / **25 users** (Premium) gebruikt hetzelfde patroon als Nextcloud maar met MKB-toegankelijkere drempels dan hun 100-user-minimum.
- **Bundle-korting 20% bij 3+ apps** beloont ecosystem-adoptie (dat is immers de propositie).
- **"Contact us voor een offerte"** bij 500+ users of maatwerk-tier, net als Nextcloud hun "Ultimate" en "Contact us" doet.
- **Per user = named user** (niet concurrent); standaard Nextcloud-billing-patroon.

### Wat de pricing-tabel NIET moet suggereren

- **Niet dat de software betaald is.** Software-indicatie prominent als "Gratis — altijd" bovenaan, zodat de Support-pricing niet verwart met software-pricing.
- **Niet dat Support verplicht is.** Een expliciete zin: *"Support is facultatief. De apps werken volledig zonder."*
- **Niet dat features achter betaling zitten.** Geen vinkjes-vergelijking die suggereert dat Standard of Premium iets *in de software* ontgrendelt.

## Support-pagina-structuur op de website

URL: **`/support`**. Linkt vanuit hoofdnavigatie (nav-label: **"Support"**; zie open vraag hieronder over "Pricing" als alternatief label).

Zes secties, in deze volgorde:

### 1. Hero

- **H1 (NL):** *"Onze apps zijn altijd gratis. Support is optioneel — voor wie meer zekerheid wil."*
- **H1 (EN):** *"Our apps are always free. Support is optional — for when you need more certainty."*
- **Lead:** korte uitleg van de propositie (2–3 regels)
- **Geen primaire CTA-knop** — dit is een informatieve pagina, niet een conversie-punt

### 2. Wat zit in Support?

Twee blokken zij-aan-zij:

- **Helpdesk-ondersteuning** — reactieve support voor vragen, bugs, problemen
- **Proactieve ondersteuning** — wij kijken mee op telemetry en waarschuwen actief bij patronen die op problemen wijzen

### 3. Pricing-tabel

De volledige pricing-tabel (hierboven gespecificeerd) met disclaimer *"Software is en blijft altijd gratis. Onderstaande prijzen gelden alléén voor het Support-abonnement."*

Toggle/sortering:
- Tier (Standard / Premium) als tab-toggle
- App-categorie als filter

Onder de tabel: bundel-korting uitgelegd, minimums toegelicht, "Contact us voor een offerte" als subtiele CTA voor bijzondere gevallen.

### 4. Hoe vraag ik Support aan?

Twee routes expliciet naast elkaar:

**Pad 1 — Je hebt een Nextcloud-leverancier**
- Neem contact op met je Nextcloud-leverancier
- Als het een officiële Nextcloud-leverancier is en ze ondersteunen Conduction: zij regelen het
- Je krijgt één contract, één factuur, één aanspreekpartij
- *(Optioneel: lijst van Nextcloud-leveranciers die onze Support aanbieden)*

**Pad 2 — Je draait Nextcloud zelf**
- Installeer de app die je onder Support wilt
- Ga naar Admin-instellingen → [AppName] → "Support aanvragen"
- Vul het formulier in — wij nemen contact op

### 5. FAQ

Minstens 6, maximaal 8 vragen:

- *"Moet ik Support hebben om de apps te gebruiken?"* — Nee, alles werkt zonder.
- *"Kan ik Support op één app hebben en niet op andere?"* — Ja.
- *"Wat als mijn Nextcloud-leverancier geen Conduction-Support aanbiedt?"* — Dan kun je altijd pad 2 volgen.
- *"Wat gebeurt er met telemetry-data?"* — Alleen met expliciete toestemming, alleen voor support-doeleinden, nooit doorverkocht.
- *"Kan ik stoppen met Support en doorgaan met de apps?"* — Ja. Opzeggen Support heeft geen impact op je gebruik van de apps.
- *"Hoe zit het met 24/7 support?"* — Beschikbaar als maatwerk-tier; neem contact op voor een offerte.

### 6. Contact-CTA

Einde pagina: *"Vragen over Support of wil je een maatwerk-offerte?"* Link naar contactformulier. Subtiel, past bij de rest van onze toon — geen gigantische conversie-CTA.

## Wat de Support-pagina NIET moet bevatten

- Geen feature-vergelijkingstabel die suggereert dat sommige app-features alleen bij Support beschikbaar zijn
- Geen add-to-cart / koop-flow
- Geen urgency-tactics ("Deze maand 10% korting")
- Geen scare-tactics ("Zonder Support ben je kwetsbaar voor...")
- Geen vergelijking met concurrenten ("Onze Support is beter dan X's Enterprise")
- Geen "Pro"-badges elders op de website die Support suggereren als gate

## Implicaties voor de app-UI (buiten scope van deze brief)

Voor pad 2 (self-managed) is er een **in-app-formulier** in de Admin-instellingen van elke app. Dat valt buiten deze website-brief, maar bij de app-UI-brief moeten we:

- Een standaard Admin-formulier-template maken voor Support-aanvraag
- Consistent in alle Conduction-apps plaatsen onder Admin → [AppName] → Support
- Vereiste velden bepalen (organisatie-naam, contact, gebruikte apps, omgeving, gewenste tier)
- Koppeling naar ons sales/CRM-systeem (PipelinQ?)
- Optioneel: een "Support status"-widget in de app-UI zelf, zodat admins zien of hun omgeving Support-gedekt is en welke tier

## Open vragen

- **Nav-label:** "Support" of "Pricing" in de hoofdnavigatie? Beide werken; "Support" is inhoudelijk accurater, "Pricing" is direct waar bezoekers op zoeken als ze kosten willen weten. Voor nu gekozen: **"Support"** (revisie na eerste mock).
- **Daadwerkelijke prijzen** — bovenstaande tabel-waarden zijn placeholders. Conduction-leiding moet reële bedragen vaststellen, bij voorkeur met benchmark-vergelijking tegen Nextcloud Enterprise en onze cost-to-serve per app.
- **Lijst Nextcloud-leveranciers** die pad 1 ondersteunen — op te stellen, nodig voor de Support-pagina.
- **Bundle-korting-percentage** — 20% is placeholder; echte waarde bepalen op basis van marge-ruimte en strategische doelen (ecosystem-adoptie aanmoedigen vs. revenue optimaliseren).
- **Revenue-share met Nextcloud** voor pad 1 — hoe werkt de verrekening precies? Af te stemmen met Nextcloud.
- **Minimum user-count** — 10 (Standard) en 25 (Premium) zijn voorstellen; kan lager als MKB-toegankelijkheid zwaarder weegt dan operationele haalbaarheid.
- **Maatwerk-tier** — 24/7, kortere responstijden. **Beantwoord:** wordt per offerte afgeprijsd op basis van Services-tarieven (Consultancy €150/uur voor contract-ontwerp + extra uren-inschatting voor out-of-hours-dekking). Zie [`services-model.md`](./services-model.md) voor de onderliggende tarievenkaart.
- **Geautomatiseerde intake** — gaat het in-app-formulier auto-ticket maken in ons CRM, of handmatig via mail? Business-proces-keuze.
