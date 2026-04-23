# Conduction SLA-model — hoe ons verdienmodel werkt

Dit document beschrijft hoe Conduction geld verdient: niet door de software achter een paywall te zetten, maar door organisaties die extra zekerheid willen een **SLA** aan te bieden. Voor het website-ontwerp is dit essentieel omdat het bepaalt welke CTA's, formulieren en pagina-structuren we wel/niet bouwen.

**Kernpunt:** de software is en blijft **altijd gratis en altijd open source**. Geen Community vs Enterprise, geen feature-gating, geen "Pro"-tier. De SLA is een **zekerheidslaag** *bovenop* de gratis software, niet een voorwaarde om de software te gebruiken.

## Wat zit er in een Conduction SLA?

Twee concrete componenten. Alles wat we beloven staat in deze lijst — als het er niet in staat, maakt het geen onderdeel uit van de SLA.

### 1. Helpdesk-ondersteuning

Reactieve support voor vragen, bugs en problemen die de klant zelf tegenkomt. Kanaal en reactietijden worden in het contract vastgelegd (typisch e-mail + ticketsysteem, werkdagen, response binnen X uur afhankelijk van severity).

### 2. Proactieve ondersteuning via telemetry

Met toestemming van de klant kijken we mee op telemetry-data van hun apps — systemen, performance, fout-patronen. We zien problemen vaak vóórdat de klant erover belt. Voorbeelden:

- Foutpatronen die zich opstapelen maar nog niet hebben geëscaleerd
- Database-groei die binnen 3 maanden tegen een drempel aanloopt
- Integraties die falen zonder dat het operationeel nog merkbaar is
- Upgrades die breken bij bekende app-combinaties

We bellen of mailen de klant dan actief: *"Hé, we zien X, we raden aan Y te doen, wil je dat we meekijken?"*

Geen SLA-klant? Dan zien we die telemetry niet (of niet-gekoppeld) en draait de klant op zichzelf.

### Wat géén onderdeel is van de SLA

Expliciet vermelden om verwachtingen te managen:

- **Geen 24/7-support** als dat niet in het contract staat (we zijn geen NOC)
- **Geen maatwerk-development** — dat is een apart project, geen SLA-onderdeel
- **Geen implementatie-begeleiding** — valt onder Services (zie [`website.md §6.7`](../website.md))
- **Geen hosting** — wij zijn geen hosting-partij; zie de twee SLA-paden hieronder
- **Geen training of advies** — ook Services, niet SLA

## De twee SLA-paden

Het verschil tussen onze twee SLA-paden is **wie de aanspreekpartij is en wie de factuur stuurt**. De inhoud van de SLA zelf is gelijk.

### Pad 1 — SLA via een Nextcloud-leverancier (gangbaarste)

**Wie herkent deze situatie:** organisaties die hun Nextcloud-omgeving *niet zelf beheren* maar afnemen bij een managed Nextcloud-partner (officiële Nextcloud-leverancier, een hosting-partij of reseller).

**Flow:**

1. Klant heeft al een Nextcloud-contract bij een leverancier (bv. een managed Nextcloud-partner)
2. Klant wil Conduction-apps gebruiken mét SLA-zekerheid
3. Klant spreekt dat af via hun eigen leverancier — één aanspreekpartij, geen verandering in leveranciers-relatie
4. Apps worden ofwel door de leverancier geïnstalleerd, ofwel door de klant zelf uit de Nextcloud app store
5. Conduction en de leverancier regelen de SLA-afspraak onderling via Nextcloud als tussenpartij (officiële Nextcloud-leverancier-route)
6. Conduction factureert de SLA-kosten via Nextcloud aan de leverancier
7. De leverancier zet (waarschijnlijk) die kosten door op zijn eigen factuur aan de klant

**Voordeel voor de klant:**

- Eén aanspreekpartij (hun Nextcloud-leverancier)
- Eén contract (uitgebreid met de SLA, niet een nieuw afzonderlijk contract met Conduction)
- Eén factuur (van hun Nextcloud-leverancier, die Conduction's SLA-kosten heeft doorgezet)
- Geen aparte relatie met Conduction opbouwen; de leverancier staat ertussen

**Implicatie voor de website:**

- Dit pad vereist **geen aankoop-flow op onze site**. De klant regelt dit met zijn leverancier, niet rechtstreeks met ons.
- Wat we wél moeten bieden: een **lijst van officiële Nextcloud-leveranciers** waarmee deze route werkt, of een verwijzing daarnaar. Mogelijk met een filter/zoek-functie: "Mijn Nextcloud draait bij [leverancier]" → check of ze Conduction-SLA-ondersteuning aanbieden.
- CTA: *"Neem contact op met je Nextcloud-leverancier om de Conduction-apps met SLA af te nemen"*

### Pad 2 — SLA rechtstreeks met Conduction (self-managed Nextcloud)

**Wie herkent deze situatie:** organisaties die hun eigen Nextcloud draaien (self-hosted, zonder leverancier, of met een leverancier die geen Conduction-SLA ondersteunt), maar toch SLA-zekerheid willen.

**Flow:**

1. Klant heeft zelf een Nextcloud draaien — niet-managed, geen officiële Nextcloud-leverancier-relatie voor support
2. Klant downloadt Conduction-apps uit de Nextcloud app store en installeert ze zelf
3. In de app — onder de Admin-settings — vult de klant een formulier in om een SLA-afspraak met Conduction aan te vragen
4. Conduction neemt contact op, stelt een SLA-contract op, factureert rechtstreeks aan de klant

**Voordeel voor de klant:**

- Geen afhankelijkheid van een Nextcloud-leverancier
- Directe relatie met de makers van de apps
- Keuze: welke apps onder SLA, welke niet (al is dit waarschijnlijk één bundel)

**Implicatie voor de website:**

- Dit pad vereist ook **geen aankoop-flow op onze site** — het SLA-formulier zit **in de app zelf**, niet op de website. Dat is een bewuste keuze: je moet de app eerst hebben om een SLA te willen, dus het formulier hoort bij de app.
- Wat we wél moeten doen op de site: **uitleggen dat pad 2 bestaat**, en dat het formulier "in de admin-instellingen van de app zelf" te vinden is.
- CTA: *"Installeer de app. In de Admin-instellingen vind je het SLA-aanvraag-formulier."*

## Gevolg voor de website-CTA-strategie

Odoo en WooCommerce hebben **"upgrade/purchase pressure"** — overal CTA's die je naar een aankoopbeslissing leiden. Bij ons is dat **"download pressure"** — overal CTA's die je naar een gratis installatie leiden. De SLA komt *later*, in het gebruik, niet in de website-funnel.

Dat betekent:

- **De primaire CTA op alle app/solution-pagina's is installeren**, niet "vraag een SLA aan"
- **"SLA"-CTA is secundair en discreet** — één duidelijke plek (SLA-pagina), niet op elke pagina
- **De SLA-pagina is informatief**, geen bestelformulier
- **Bestel-flow zit elders** — pad 1 bij de leverancier, pad 2 in de app

De SLA is geen funnel-doel van de website. Het is een *vervolg* dat we duidelijk uitleggen zodat klanten weten dat het kan, maar er komt geen shopping-cart op deze site.

## Wat de SLA-pagina op de website moet bevatten

Eén pagina — bereikbaar via footer-link "SLA" of "Support" — met deze secties:

### 1. Wat is onze SLA? (hero + korte uitleg)

*"Onze apps zijn altijd gratis. Voor organisaties die meer zekerheid nodig hebben, bieden we een SLA: helpdesk-ondersteuning en proactieve begeleiding op basis van telemetry. Niet verplicht, wel beschikbaar."*

### 2. Wat zit erin?

Twee blokken:
- **Helpdesk-ondersteuning** — reactieve support voor vragen, bugs, problemen
- **Proactieve ondersteuning** — wij kijken mee op telemetry en waarschuwen actief bij patronen die op problemen wijzen

Zonder vage claims. Concrete formulering van wat je wel en niet krijgt.

### 3. Hoe vraag ik een SLA aan?

Twee routes expliciet naast elkaar:

**Pad 1 — Je hebt een Nextcloud-leverancier**
- Neem contact op met je Nextcloud-leverancier
- Als het een officiële Nextcloud-leverancier is en ze ondersteunen Conduction: zij regelen het
- Je krijgt één contract, één factuur, één aanspreekpartij
- (Optioneel: een lijst van Nextcloud-leveranciers die onze SLA ondersteunen)

**Pad 2 — Je draait Nextcloud zelf**
- Installeer de app die je onder SLA wil hebben
- Ga naar Admin-instellingen → [AppName] → "SLA aanvragen"
- Vul het formulier in — wij nemen contact op

### 4. Wat zijn de voorwaarden?

Niet in detail op de website (dat komt in het contract). Wel:
- Algemene responstijden per severity-niveau
- Wat we doen bij een incident
- Hoe telemetry werkt (privacy, welke data, opt-in/out)
- Looptijd en opzeg-termijnen (hoog over)

### 5. Wat zijn de kosten?

**Niet op de pagina.** Deze informatie is situatie-afhankelijk (welke apps, welke omgeving, welke responstijden) en past niet in een prijslijst. In plaats daarvan: *"Neem contact op voor een offerte"* of *"Vraag een SLA aan via je Nextcloud-leverancier"*.

Uitzondering: als de markt een prijs-indicatie verwacht, "**Vanaf €X per app per maand**" kan, maar alleen als we vanaf-waardes hebben die we eerlijk kunnen garanderen. Als niet: geen prijs.

### 6. FAQ

Veelgestelde vragen, bijvoorbeeld:

- *"Moet ik een SLA hebben om de apps te gebruiken?"* — Nee, alles werkt zonder SLA.
- *"Kan ik een SLA op één app hebben en niet op andere?"* — In principe ja, maar prakisch meestal op bundel-niveau.
- *"Wat als mijn Nextcloud-leverancier geen Conduction-SLA aanbiedt?"* — Dan kun je altijd pad 2 volgen: SLA rechtstreeks met ons.
- *"Wat gebeurt er met telemetry-data?"* — Alleen met expliciete toestemming, alleen voor support-doeleinden, nooit doorverkocht.
- *"Kan ik stoppen met de SLA en doorgaan met de apps?"* — Ja. Opzeggen SLA heeft geen impact op je gebruik van de apps.

### 7. Contact-CTA

Einde pagina: *"Vragen over de SLA? Neem contact op."* Link naar contactformulier. Geen gigantische CTA — past bij de rest van onze toon.

## Wat de SLA-pagina NIET moet bevatten

- Geen pricing-vergelijking (wij hebben geen gratis vs betaald-variant van de software)
- Geen add-to-cart / koop-flow
- Geen urgency-tactics ("Deze maand 10% korting")
- Geen scare-tactics ("Zonder SLA ben je kwetsbaar voor...")
- Geen vergelijking met concurrenten ("Onze SLA is beter dan X's Enterprise")
- Geen feature-vergelijkingstabel die suggereert dat sommige features alleen bij SLA beschikbaar zijn

De toon moet zijn: *"Hier is hoe we ons brood verdienen. Het is optioneel. Als je het wilt, dit is hoe."*

## Implicaties voor de app-UI (niet voor deze brief, wel noemen)

Voor pad 2 (self-managed) is er een **in-app-formulier** in de Admin-instellingen van elke app. Dat valt buiten de scope van deze website-brief — maar bij de vervolgstappen (app-UI-brief) moeten we:

- Een standaard Admin-formulier-template maken voor SLA-aanvraag
- Consistent in alle Conduction-apps plaatsen onder Admin → [AppName] → SLA
- Vereiste velden bepalen (organisatie-naam, contact, gebruikte apps, omgeving, gewenste responstijden)
- Koppeling naar ons sales/CRM-systeem (PipelinQ?)

Dit is een apart design-traject. Noteren in de [open vragen van de hoofdbrief](../website.md).

## Relatie met onze andere diensten

Om verwarring te voorkomen:

| Wat | Voor wie | Hoe afgerekend | Voorbeeld |
|---|---|---|---|
| **Apps** | Iedereen | Gratis | OpenCatalogi installeren |
| **SLA** | Klanten die zekerheid willen | Abonnement, via leverancier of direct | Reactieve + proactieve support op geïnstalleerde apps |
| **Services** | Klanten met specifieke behoefte | Uurtarief / projectprijs | Implementatie-begeleiding, training, maatwerk-ontwikkeling |
| **Partnerschap** | Nextcloud-leveranciers | Revenue share via Nextcloud | Leverancier verkoopt Conduction-SLA aan zijn klanten |

Deze vier vormen de totale Conduction-propositie. Op de website zijn Apps en SLA zichtbaar. Services is een discrete pagina. Partnerschap is voorlopig geen website-content (dat regelen we via Nextcloud-kanalen).

## Open vragen die deze brief niet oplost

- Welke Nextcloud-leveranciers bieden onze SLA nu al aan? (Nog op te stellen lijst.)
- Wat is de minimale/startgrootte van een SLA-contract? (Nog te bepalen.)
- Hoe werkt de Nextcloud-verrekening in de praktijk exact (revenue-share-percentage, facturatie-cadans, admin-aspecten)? (Met Nextcloud af te stemmen.)
- Is er een geautomatiseerd intake-proces vanuit het in-app-formulier, of gaat alles handmatig via mail? (Business-proces-keuze, relevant voor volume-beheer.)
- Willen we een "SLA status"-widget in de app-UI zelf, zodat admins zien of hun omgeving SLA-gedekt is? (UX-beslissing, app-UI-brief.)
