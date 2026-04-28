# Platform benchmarks — Odoo, WooCommerce & Nextcloud

Uitgebreide analyse van drie volwassen app-/extensie-platforms: **Odoo** (odoo.com, ERP-ecosystem met 30.000+ apps), **WooCommerce** (woocommerce.com, e-commerce-plugin voor WordPress met een extensie-marketplace), en **Nextcloud** (nextcloud.com — het moeder-platform waarop onze apps draaien en dat structureel het dichtst bij ons model zit: free core + paid support).

Alle drie: open-source-cores met een uitgebreide catalogus, en duidelijke discovery-/install-flows die voor ons relevant zijn. Nextcloud is tegelijk onze **directe benchmark voor het verdienmodel** (vrije software + betaald support/SLA-abonnement) én onze **host-ecosystem** (we zitten erin).

## Context — ons model vs het hunne

Voordat we patronen overnemen: hun business-model is fundamenteel anders dan het onze, en dat bepaalt **wat we wel en niet adopteren**.

| | Conduction | Odoo | WooCommerce |
|---|---|---|---|
| Core-prijs | **Gratis** (altijd) | Community Edition gratis; Enterprise betaald (per user/mo) | Core-plugin gratis |
| App/extensie-prijs | **Gratis** (altijd) | Community apps gratis; Enterprise apps achter paywall; 3rd-party apps betaald of gratis | Meeste extensies betaald (abonnement of one-time) |
| Support-model | **Optioneel Support-abonnement** (technisch: SLA) tegen betaling | SLA gekoppeld aan Enterprise-abonnement | Individuele extensie-vendors leveren support |
| "Add to cart"-flow nodig? | Nee — install via Nextcloud app store | Ja — trial/buy flow | Ja — e-commerce |
| User accounts op de site nodig? | Nee — alles public | Ja voor trial + portal | Ja voor aankopen + downloads |
| Partner-directory? | Optioneel later | Ja, uitgebreid ("Find a partner") | Ja ("Agency directory") |

**Implicatie:** we nemen structurele patronen over (IA, catalogus-UX, detail-pagina-template, filter-systemen) maar **niet** commerciële mechanica (cart, checkout, subscription-management, in-site-accounts). Onze "conversie" is niet een aankoop — het is een klik naar de Nextcloud app store. Dat maakt onze site *eenvoudiger* dan die van hen.

**Bijkomstige implicatie:** waar zij hun "free core" als **acquisition-funnel** gebruiken (gratis om je te laten upgraden), is bij ons de "free" niet een trechter maar de **eindstaat**. Dat geeft ons de vrijheid om de commerciële druk weg te laten — geen "Talk to sales"-CTA's op elke pagina, geen urgency-gedrag, geen "Upgrade"-toasts. De Support-pagina mag gewoon in de hoofdnav staan zolang de pagina-content zelf duidelijk maakt dat het optioneel is en de software altijd gratis blijft.

---

## Odoo — deep dive

### Platform-context

- ~50K GitHub-stars op het hoofd-repo, miljoenen gebruikers
- ~30–40 "officiële" apps (Accounting, CRM, Sales, Inventory, HR, Website, Marketing, Productivity, ...) plus ~30.000 third-party apps in de marketplace
- Openly bilingual+, feitelijk meertalig (15+ talen)
- Community vs Enterprise split is de centrale spanning van het hele verhaal

### Informatie-architectuur van odoo.com

De hoofdnavigatie (sticky header) heeft ruwweg deze structuur:

- **Apps** → dropdown per categorie (Finance, Sales, Services, Operations, HR, Marketing, Productivity, Websites, Customization). Elke categorie toont 4–8 apps als mini-kaarten + "View All".
- **Industries** → "Retail", "Construction", "Healthcare", etc. — solution-achtige pagina's per sector.
- **Community** → Events, partners, forum, GitHub, contribute.
- **Services** → Consultancy / implementatie / training. Hier zit de sales-funnel.
- **Pricing** → pricing-pagina (Enterprise-model).
- **Sign in / Try it free** → rechts, primary buttons.

**Opvallend:**
- "Apps" is duidelijk de **hoofdingang**, met een mega-menu (dropdown met preview-kaarten en screenshots). Niet alleen links — je ziet het product al voor je klikt.
- "Industries" bestaat náást "Apps". Dat is hun versie van wat wij "Solutions" noemen. Belangrijk verschil: Odoo heeft er géén aparte tab voor per functie-probleem ("WOO-compliance") maar voor sectoren ("Construction"). Meer top-down gestructureerd.
- "Try it free" en "Sign in" zijn dominant rechts in de header. Bij ons wordt dat niet "Try it free" (we hebben geen trial — je installeert gewoon) en geen "Sign in" (we hebben geen account).

### Homepage-strategie

De homepage is een scroll-marathon met ruwweg 8–12 secties in vaste volgorde:

1. **Hero** — grote headline ("All-in-one business suite"), een screenshot of 3D-mockup van de Odoo UI, primary CTA "Start now — it's free", secondary CTA "Meet an expert"
2. **Stats-strip** — "7+ million users", "+200 countries", "+4.000 apps" — social proof in cijfers
3. **App grid** — 9–12 apps als kaarten met icoon en naam, "See all apps →"
4. **Industry-teasers** — "Odoo for [Retail/Manufacturing/...]" met representatieve schermen
5. **Demo-CTA strip** — "Try it with your data — no commitment"
6. **Testimonial-section** — logo-wall van grote klanten + 1 case-quote
7. **Pricing-teaser** — "One price, all apps" — Enterprise-model in één blok
8. **Community-blok** — GitHub-sterren, forum-leden, contributor-count
9. **Footer** — enorm, 6–8 kolommen, alle sub-links gesorteerd

**Patronen die relevant zijn voor ons:**

- **App-grid direct op de homepage** (sectie 3) — wij gaan dit ook doen; de apps zijn de hoofdrol.
- **Stats-strip als social proof** (sectie 2) — bij ons zou dat zijn: "11 core apps", "100+ gemeenten", "Installable from Nextcloud app store in <2 minutes". Cijfers die onze claim ondersteunen, geen vage "toonaangevend"-taal.
- **Community-blok** (sectie 8) — relevant omdat wij ook OSS zijn. "X GitHub-stars, Y contributors, Z forks" versterkt de open-source-positionering.

**Patronen die voor ons *niet* werken:**

- **Demo-CTA strip** (sectie 5) — Odoo pusht "try with your data". Bij ons is de equivalente stap "install from app store" en dat kan gewoon op de app-pagina zelf, niet als aparte hero-strip.
- **Testimonial-logo-wall** (sectie 6) — goed patroon op zich, maar vraagt klantlogo-toestemming die we nog niet hebben. Voor nu een placeholder of plaatsen in een "proof"-sectie later.
- **Pricing-teaser** (sectie 7) — wij hebben geen prijs per app voor de software zelf. Wat wij hier zouden kunnen zetten is een **Support-teaser**: *"Alles gratis. Zelfstandig genoeg? Perfect. Meer zekerheid nodig? Bekijk onze Support-tiers."* Dat draait de conversatie om — géén prijs-wall, maar optionele bovenlaag.

### Apps-catalogus (apps.odoo.com en /apps)

Odoo heeft twee catalogi die goed te onderscheiden zijn:

**1. `/apps` op odoo.com** — de *officiële* Odoo-apps (ontwikkeld door Odoo zelf, onderdeel van Community of Enterprise). Gepresenteerd in thematische secties (Finance, Sales, ...) met uniforme app-kaarten. Elke kaart heeft icoon, naam, één-regel-tagline, "Learn more".

**2. `apps.odoo.com`** — een **separate subdomein** met de hele third-party marketplace. Zwaar gecommercialiseerd: prijzen prominent, add-to-cart, downloads-teller, reviews en sterren, installeer-vereisten (Odoo-versie), publisher-profiel. Feitelijk een app store-UI met filter-sidebar en een eindeloze grid.

**Filter-systeem op apps.odoo.com:**
- Categorie (Accounting, Sales, Marketing, ...)
- Prijs (Free / Paid / Under €50 / €50–100 / €100+)
- Odoo-versie (compatibiliteit)
- Sterrenwaardering
- Trending / Newest / Best-rated
- Publisher

**Detail-pagina per app op apps.odoo.com:**
- Hero: icoon + naam + publisher + versie + prijs + "Buy Now"-CTA
- Screenshots-carousel (3–10 images)
- "Features"-blok (bullet-list)
- "Installation"-instructies
- "Compatibility" (Odoo-versies, OS)
- Reviews-sectie (sterren + geschreven feedback + verified-buyer-badge)
- Publisher-profiel met andere apps van dezelfde publisher
- FAQ
- Support-info (wie, hoe snel, waar)

**Patronen om over te nemen:**

- **Filter-systeem met multi-facet** (categorie × compatibiliteit × status) past één-op-één op onze apps-catalogus. Onze categorie is `solutions` of een eigen taxonomie (registers / documents / integrations / ...), onze compatibiliteit is Nextcloud-versie.
- **Detail-pagina-structuur** — hero + screenshots + features + installation + compatibility + support is de klassieker en werkt omdat hij voor elke app hetzelfde voelt. Ons app-detail in §6.3 van de hoofdbrief gebruikt exact deze opbouw.
- **Publisher-profiel** — voor Conduction is de "publisher" altijd hetzelfde (ons), dus dit is bij ons irrelevant. Maar als we in de toekomst third-party apps op onze site tonen (community-apps), wordt dit wel relevant.

**Patronen om *niet* over te nemen:**

- **Add-to-cart en prijs** — geen. Onze CTA is *"Install from Nextcloud app store"*, dat is een doorverwijzing, geen aankoop.
- **Reviews/sterren op de marketing-site** — de Nextcloud app store heeft eigen ratings. Dupliceren zou óf scheefgetrokken zelf-gerapporteerde cijfers geven óf een pull-in via een API-integratie vereisen. Voor MVP skippen.
- **Publisher-profiel + "other apps by"** — niet nodig; wij zijn de enige publisher. Vervangen door "Integreert met" (andere Conduction-apps) zoals in §6.3 van de brief.
- **Twee aparte catalogi (officieel + third-party)** — splitst de aandacht en vraagt een complexe subdomein-strategie. Wij hebben één catalogus voor al onze apps en tonen "Integreert met" voor de samenhang.

### Individuele app-pagina (bv. odoo.com/app/crm)

Voor de *officiële* apps heeft Odoo per app een eigen marketing-pagina onder `/app/[slug]`, apart van apps.odoo.com. Deze pagina is heel anders — veel marketing-vlees, veel scroll, screenshot-heavy. Ruwweg:

1. **Hero** — grote headline ("The open-source CRM"), een full-width screenshot met 3D-tilt, primary CTA "Start now — it's free"
2. **Sub-navigatie** — sticky intra-page-nav (Features / Customers / Documentation / Pricing) die meescrollt
3. **Feature-blokken** — 8–15 alternerende secties met tekst-links-beeld-rechts (of vice versa). Elke sectie pitcht één feature met een screenshot en 2–3 regels tekst.
4. **Integration-strip** — logo's van gekoppelde systemen
5. **Customer-story** — één uitgelicht verhaal met klant-logo, quote, metriek
6. **Pricing-blok** — "Free in Community / X per user in Enterprise"
7. **Final CTA** — grote hero-herhaling onderaan
8. **Standaard footer**

**Opvallend:**

- De sub-navigatie (sticky intra-page) werkt goed op lange product-pagina's. Onze app-detail-pagina's zouden deze ook kunnen gebruiken.
- De feature-blokken alterneren van uitlijning (tekst-links/beeld-rechts → beeld-links/tekst-rechts). Dat houdt een lange pagina visueel leesbaar.
- Screenshots zijn **overal** — elke bewering wordt ondersteund door een UI-shot. Voor ons betekent dat: we moeten echt screenshots hebben per app voordat deze pagina's bouwbaar zijn.

**Aanbeveling:** de structuur (hero + sticky sub-nav + alternerende feature-blokken + integration-strip + CTA) is overneembaar. De lengte van de Odoo-pagina (scroll-marathon van 15+ secties) is *te lang* voor ons MKB-publiek dat snel een beslissing wil maken. Wij mikken op 5–8 secties.

### Community vs Enterprise-split

Dit is misschien het meest intrigerende patroon van Odoo, en bijna 1-op-1 het *inverse* van ons model.

Odoo zet Community Edition en Enterprise Edition neer als "twee versies van hetzelfde product". Community is open-source, gratis, maar feature-gated: je mist accounting-modules, mobile-apps, IoT-integraties, advanced reporting, etc. Enterprise krijgt alles + hosted + support + SLA + upgrades.

**Visuele presentatie op de pricing-pagina:**

Twee kolommen zij-aan-zij. Vinkjes per kolom per feature. Enterprise staat rechts (visueel dominant), Community links (minder prominent). Prijs is "Free" voor Community en "$X per user per month" voor Enterprise. Enterprise-kolom heeft een zachte glow/border of een "Recommended"-badge.

**Wat wij hieruit meenemen:**

Ons model is géén feature-gated-split. Alle features van alle apps zijn altijd open source en gratis. Maar wij hebben wél een optionele Support-laag met twee tiers (Standard en Premium, zie [`support-model.md`](./support-model.md)). Die kunnen we visueel op een soortgelijke manier presenteren als Nextcloud's tier-kolommen:

Drie kolommen:
- **"Self-hosted"** (gratis, altijd) — geen Support-abonnement, de default
- **"Support Standard"** (betaald, optioneel) — helpdesk + proactieve rapporten
- **"Support Premium"** (betaald, optioneel) — helpdesk + proactieve alerts + upgrade-begeleiding

Alle drie kolommen tonen **dezelfde software-features** (want de software is identiek). Het verschil zit uitsluitend in *support-response-tijden, proactieve monitoring, en upgrade-assistentie*. Niet in functionaliteit van de apps.

**Kritisch verschil:** bij Odoo lees je op de feature-pagina's subtiel "alleen in Enterprise". Bij ons mag dat nooit voorkomen — dat zou ons model tegenspreken. Elke app-feature moet *onvoorwaardelijk* beschikbaar zijn.

### Services / partners-directory

Odoo heeft een uitgebreide partners-/consultants-directory ("Find a Local Partner") met:
- Filter op regio, sector, certificatie-niveau (Ready, Silver, Gold)
- Partner-profielen met case-studies
- "Request a quote"-flow

Dit is hun implementatie-net, niet een vervanger voor Enterprise maar een aanvulling.

**Bij ons:** Services in de footer, met een discrete pagina die vertelt dat wij ook implementatie en training doen. Geen uitgebreide partner-directory nodig voor MVP — dat is eerder relevant als we een partner-netwerk opbouwen (nu is Conduction zelf de implementator).

### Patronen om van Odoo over te nemen

| # | Patroon | Hoe bij ons |
|---|---|---|
| 1 | Mega-menu "Apps" met preview-kaarten in header | Ja, lichter — geen 3D-mockups, wel hexagon-logo + naam + tagline |
| 2 | Stats-strip op homepage | Ja — "11 apps", "100+ gemeenten", "install in <2 min" |
| 3 | Multi-facet filter op apps-catalogus | Ja — categorie × status × Nextcloud-versie × NLDS-compliance |
| 4 | Detail-pagina met sticky intra-page-nav | Ja voor app-detail, alternerende feature-blokken |
| 5 | Alternerend tekst/beeld in feature-secties | Ja |
| 6 | Community/Enterprise-kolom-vergelijking op pricing | **Aangepast: Self-host / Support Standard / Support Premium** met dezelfde software-features-lijst voor alle kolommen; verschil alleen in support-response-tijd en proactieve monitoring |
| 7 | Integration-strip op app-pagina | Ja — andere Conduction-apps als logo-strip |
| 8 | Footer met 6–8 kolommen | Ja, maar compacter (4–5 kolommen lijkt ons voldoende) |

### Patronen *niet* overnemen

| # | Patroon | Waarom niet |
|---|---|---|
| 1 | Twee aparte catalogi (officieel + marketplace) | Te complex; wij hebben één catalogus |
| 2 | Add-to-cart en prijs op apps | Geen aankoop-flow; we verwijzen naar Nextcloud app store |
| 3 | Reviews/sterren-systeem | Dupliceert Nextcloud app store; scope creep |
| 4 | "Try it free" trial-flow | Geen trial; apps installeer je direct |
| 5 | Upgrade-druk in UI ("This is Enterprise-only") | Botst met ons gratis-voor-altijd-model |
| 6 | Scroll-marathon van 15+ secties per pagina | Te lang voor MKB-publiek |
| 7 | Uitgebreide partners-directory | Premature; Conduction is nu zelf de partner |

---

## WooCommerce — deep dive

### Platform-context

- De grootste e-commerce-plugin voor WordPress, GPL-licensed
- Core-plugin gratis (installeerbaar vanuit WP-admin)
- Uitgebreide extensie-marketplace met honderden paid-extensions
- Acquired door Automattic (de WordPress.com-moederorganisatie)
- Veel kleinere, onafhankelijke vendors leveren extensies

### Informatie-architectuur van woocommerce.com

Hoofdnavigatie:
- **Sell online** / "Why WooCommerce" → pitch-pagina's
- **Product** → feature-pagina's
- **Extensions** → marketplace (woocommerce.com/products)
- **Themes** → gallery
- **Pricing** → (sinds een tijdje) gepresenteerd als "free core + paid add-ons"
- **Resources** → docs, blog, tutorials
- **For experts** → agency-directory, developer-docs
- **Log in / Get started** → rechts

**Opvallend:**

- "Extensions" en "Themes" zijn **beide** hoofdingangen — gescheiden catalogi. Extensies = functionaliteit. Themes = uiterlijk.
- "For experts" is een aparte sectie voor ontwikkelaars en agencies — parallel aan de primaire marketing-site.
- Geen duidelijk "Community vs Enterprise"-patroon — het model is anders (free core + losse paid extensions).

### Homepage-strategie

De homepage is minder scroll-intensief dan Odoo maar even gestructureerd:

1. **Hero** — "Start, run and grow your business" — headline, screenshot van WooCommerce admin-UI, primary CTA "Start a new store", secondary CTA "Learn more"
2. **Feature-teasers** (4 blokken) — "Open source", "Ownership of data", "Unparalleled flexibility", "Expertise at hand"
3. **Extensions-teaser** — "Customize your store with 700+ extensions" met 4–6 logo-tiles + "Browse all"
4. **Stats-strip** — "# of stores built on WooCommerce", "# of countries", "# of downloads"
5. **Customer-stories** — grid van 3 case-studies met foto/logo + outcome-quote
6. **Agency-teaser** — "Need help? Hire an expert from our agency directory"
7. **Developer-teaser** — "Building something new? Check our developer docs"
8. **Final CTA** — "Start your store today"
9. **Footer** — uitgebreid, 6 kolommen

**Patronen relevant voor ons:**

- **Values als feature-teasers** (sectie 2) — "Open source", "Ownership of data" zijn prominent, niet technische features. Dat past bij hoe wij onszelf positioneren (ownership, transparency, no lock-in). Onze hero zou ditzelfde kunnen doen: "Open source. Eigen Nextcloud. Geen vendor lock-in."
- **Extensies-teaser als tweede-na-hero** (sectie 3) — plaatst het ecosystem direct na de pitch, precies zoals wij apps willen plaatsen.
- **Stats-strip** (sectie 4) — zelfde patroon als Odoo.

**Patronen die voor ons niet werken:**

- **Agency-teaser en Developer-teaser op homepage** (sectie 6 + 7) — wij hebben deze doelgroepen (integrators) maar ze zijn tertiair, niet voor de homepage. Footer is genoeg.

### Extensions-store

Dit is het hart van WooCommerce's website-model en waar we het meest van leren.

**URL:** `woocommerce.com/products/`

**Layout:**

- Filter-sidebar links (sticky op desktop): Categorieën (Payments, Shipping, Marketing, Product, Store management, ...), Prijs-model (One-time, Subscription, Free), Rating, Tag.
- Grid met extensie-kaarten rechts.
- Elke kaart: logo/icoon, naam, publisher, één-regel-tagline, prijs ("From $X/year" of "Free"), rating-sterren.
- Sortering: Popular / Newest / Alphabetical / Price.
- Sub-navigatie boven: "All extensions" / "Popular" / "New" / "Themes".

**Detail-pagina per extensie** (`/products/[slug]`):

- **Hero** — extensie-naam + publisher (als klikbare link naar publisher-pagina) + versie + "Add to cart" / "Get it free" + prijs-info met billing-opties (annual/monthly)
- **Tabbed content** — Description / Reviews / Documentation / FAQ — als sticky tab-bar
- **Description-tab** — screenshots + feature-lijst + use-cases
- **Reviews-tab** — sterren + geschreven reviews + verified-buyer + response-from-developer
- **Documentation-tab** — linkt naar externe docs
- **FAQ-tab** — 5–10 veelgestelde vragen
- **Sidebar** — versie, last updated, minimum WooCommerce-versie, tags, categorie, pricing-breakdown
- **"More from this publisher"** — andere extensies van dezelfde maker

**Patronen om over te nemen:**

- **Filter-sidebar + grid-layout** is standaard maar Wordt hier heel strak uitgevoerd. Facets zijn compact en niet overweldigend.
- **Tabbed content op de detail-pagina** — Description / Reviews / Docs / FAQ. Dit scheidt marketing van documentatie. Voor ons: Description / Screenshots / Docs / FAQ werkt.
- **Sidebar met technische metadata** — versie, last-updated, compatibility, licentie. Precies wat techneuten willen zien voor ze installeren. Onze equivalent: Nextcloud-versie, laatste release, NLDS-compliance, licentie, GitHub-link.

**Patronen om *niet* over te nemen:**

- **Add-to-cart en prijsinformatie** — geen aankoop. Onze CTA is "Install from Nextcloud app store".
- **Reviews-tab** — Nextcloud app store heeft eigen reviews. Dupliceren is scope creep.
- **"From this publisher"-sectie** — wij zijn altijd de publisher.

### Themes gallery

WooCommerce heeft een separate themes-gallery voor WordPress/WooCommerce-themes:

- Grid met theme-screenshots, titel, prijs, "Live demo" en "Buy now"
- Filter op categorie, kleurpalet, features
- Preview-mode (live demo)

**Voor ons:** geen themes-sectie nodig. Onze "look" is vast (theme-conduction-2026). NLDesign is strikt genomen een thema-integratie, maar dat positioneren we als app, niet als theme-gallery-entry.

### Agency / expert directory

WooCommerce heeft een "WooExperts"-programma — geverifieerde agencies en freelancers die WooCommerce-projecten doen. Per agency: specialisaties, regio, contact-formulier, case-studies.

**Bij ons:** zie Odoo-analyse — voor MVP skippen; discrete Services-pagina is genoeg.

### Developer-hub

`developer.woocommerce.com` is een aparte subdomein met API-docs, extensie-ontwikkelings-guides, hooks-reference. Zeer technisch, zeer grondig.

**Bij ons:** `docs.conduction.nl` (bestaand Docusaurus) vervult deze rol. Geen aparte developer-subdomein nodig.

### Patronen om van WooCommerce over te nemen

| # | Patroon | Hoe bij ons |
|---|---|---|
| 1 | Values als hero-teasers ("Open source", "Ownership of data") | Ja — onze versie: "Open source. Eigen Nextcloud. Geen vendor lock-in." |
| 2 | Extensies-teaser als tweede homepage-sectie | Ja — apps direct na hero |
| 3 | Filter-sidebar + grid op catalogus | Ja — identieke structuur |
| 4 | Tabbed content op detail-pagina (Description / Docs / FAQ) | Ja |
| 5 | Sidebar met technische metadata (versie, compatibility, licentie) | Ja |
| 6 | Eenvoudige homepage (6–9 secties, geen scroll-marathon) | Ja — mikken op 6–8 secties |

### Patronen *niet* overnemen

| # | Patroon | Waarom niet |
|---|---|---|
| 1 | Add-to-cart / pricing op extensies | Geen aankoop-flow |
| 2 | Reviews-tab | Dupliceert Nextcloud app store |
| 3 | Themes-gallery | Geen theme-keuze; één vaste stijl |
| 4 | WooExperts-directory | Premature |
| 5 | Subscription-vs-one-time keuze op extensies | Geen relevant onderscheid bij ons |

---

## Nextcloud — derde benchmark (free core + paid support)

### Platform-context

Nextcloud is waar onze apps in draaien, en structureel de benchmark die het dichtst bij ons model staat: **core is gratis en open source, support wordt verkocht als abonnement**. De app-store (apps.nextcloud.com) is volledig gratis; hun omzet komt uit Enterprise-subscriptions met SLA-support.

Dat maakt Nextcloud specifiek relevant voor onze Support-pagina en pricing-structuur. Voor de app-catalogus-UX is Nextcloud's app store (apps.nextcloud.com) óók leerzaam — dat is de plek waar onze apps feitelijk gedownload worden.

### Nextcloud's pricing-structuur (exact, per `/pricing` op nextcloud.com)

Nextcloud rekent **per user per jaar** met drie tiers en een **100-user-minimum** (met volume-korting vanaf 200):

| Tier | Files-subscription | Talk-subscription | Minimum | Inclusief |
|---|---|---|---|---|
| **Standard** | €71,29/user/year (100 users)<br>€53,17/user/year (200+ users) | €42/user/year (100 users)<br>€31,50/user/year (250+ users) | 100 users | File sync & share, enterprise-capabilities, portal + email support (business hours), 2 werkdagen responstijd, 1-jaar maintenance-lifecycle |
| **Premium** | €104,99/user/year (100)<br>€81,99/user/year (200+) | — | 100 users | Alles van Standard + extended support, clustered instances, 5+ jaar maintenance, 1 werkdag responstijd, extended business hours email |
| **Ultimate** | €204,75/user/year (100)<br>€183,75/user/year (200+) | — | 100 users | Alles van Premium + Nextcloud Assistant, Flow, Whiteboard, SIP-bridge, MS-integraties, advanced apps, 1-24/7 telefoon-support |

Alle prijzen **ex. BTW**, jaarlijkse contracten, volume-korting vanaf 200 users, "contact us for quotes" voor grotere organisaties. Add-ons (Talk, Groupware, Office) apart verkrijgbaar.

### Structurele observaties voor ons

**Wat Nextcloud goed doet en we overnemen:**

- **Per user × per jaar** als billing-eenheid — standaard in deze markt, makkelijk te begrijpen, past bij software-as-subscription-verwachtingen.
- **Tiers met escalerende responstijden** — Standard 2 werkdagen → Premium 1 werkdag → Ultimate 24/7. Duidelijke ladder, elke klant vindt z'n plek.
- **Volume-korting** via user-count-tranches (100 vs 200+). Rechtvaardigt hogere prijs bij lage aantallen (kosten om te serveren is relatief hoog bij kleine klanten) en beloont grotere deployments.
- **"Contact us" voor Ultimate/custom** — hoog-volume en maatwerk onttrekken zich aan de prijslijst.
- **Transparante prijzen op de site** — geen "call sales to get a quote" voor de standaardtiers. Dat vertrouwen geven wij ook.
- **Comparison-tabel met drie kolommen** als visuele structuur — werkt goed voor "kies jouw tier"-keuze.

**Waar wij structureel afwijken:**

| | Nextcloud | Conduction |
|---|---|---|
| **Wat wordt verkocht?** | Software + support, gebundeld | Alléén support — software is en blijft gratis |
| **Minimum user-count** | 100 users | 10 users (Standard), 25 users (Premium) — MKB-toegankelijker |
| **Aantal tiers** | 3 (Standard/Premium/Ultimate) | 2 (Standard/Premium) — eenvoudiger |
| **Per app of per stack?** | Per stack (Files-subscription dekt alle apps) | Per app — kies welke apps je onder Support wilt |
| **Bundel-korting** | Impliciet (tiers dekken alles) | Expliciet (20% bij 3+ apps) — beloont ecosystem-adoptie |
| **"Software is gratis"-framing** | Impliciet (community edition bestaat) | Expliciet (headline op pricing-pagina) |

De kern-framing-verschil: bij Nextcloud koop je een abonnement dat *toegang* geeft tot enterprise-features én support. Bij ons koop je alleen support; toegang tot alles is altijd gratis. Dat moet prominent en eerlijk gecommuniceerd op onze Support-pagina.

### Nextcloud's pricing-pagina als visueel referentiepunt

- **3-kolommen-layout** met tier-vergelijking (Standard / Premium / Ultimate)
- **Prijs vet boven**, per-user-year-notatie consistent
- **Features-lijst per kolom** met vinkjes/bullets; expliciet welke features bij welke tier
- **"Most popular"-badge** op Premium (middelste kolom)
- **"Contact us" CTA's** op pricing-tiers voor >200 users
- **Toggle** tussen annual / monthly billing (waar van toepassing)

Wij lenen het 2-kolommen-patroon (Standard/Premium) + prijs-vet-boven + features-per-kolom. Toegevoegd: een 3e dimensie voor **app-keuze** (tabel in plaats van drie kolommen, of toggle per app-categorie — zie [`support-model.md`](./support-model.md)).

### Nextcloud's app store (apps.nextcloud.com)

Dit is waar onze apps daadwerkelijk gedownload worden. Structuur van apps.nextcloud.com is vrij simpel:

- Hoofdnav: categorieën (Files, Productivity, Tools, Social, Multimedia, Games, etc.)
- Grid met app-kaarten: icoon, naam, publisher, rating, korte tagline
- App-detail-pagina: hero + description + screenshots + version-history + ratings + comments + install-instructions
- Zoek + filter op compatibiliteit met Nextcloud-versie

**Voor ons relevant:** onze apps zullen hier verschijnen. De "Install from Nextcloud app store"-CTA op onze eigen site linkt naar een van deze detail-pagina's. Consistentie tussen onze site en de Nextcloud-app-store-pagina (logo, tagline, screenshots) is een UX-goed: de bezoeker herkent de app van onze site terug op de app-store-pagina.

**Actie-item voor de roll-out:** zorg dat onze Nextcloud-app-store-entries dezelfde tagline, korte beschrijving en screenshots gebruiken als de app-detail-pagina op www.conduction.nl. Gedefinieerd in [`app-taglines.md`](./app-taglines.md).

## Odoo + WooCommerce + Nextcloud vs Conduction — synthese

Beide platforms delen, ondanks hun verschillen, een paar kernpatronen:

1. **Mega-menu voor apps/extensies in de header** — laat zien voordat je klikt.
2. **Apps/extensies-grid direct na hero op homepage** — ecosystem is de hero-vervolg.
3. **Filter-sidebar + grid voor catalogus** — multi-facet.
4. **Detail-pagina-template:** hero + screenshots + tabs (description/docs/faq) + metadata-sidebar.
5. **Stats-strip als social proof** — cijfers i.p.v. claims.
6. **Community / OSS-blok** — zichtbaar GitHub-integratie.
7. **Uitgebreide footer** met secundaire navigatie.

Deze **zeven patronen nemen we één-op-één over**, met aanpassingen voor onze simpelere conversie (klik naar app store i.p.v. aankoop).

### Waar wij fundamenteel van beiden afwijken

| Aspect | Odoo/Woo | Conduction |
|---|---|---|
| Primaire conversie | Trial / aankoop / abonnement | Klik naar Nextcloud app store |
| Account-concept | Inlog + portal noodzakelijk | Geen; alles public |
| Pricing-pagina | Centraal element van het verhaal, prijzen voor software + support bundled | Pricing-pagina bestaat (als Support-pagina) in hoofdnav, maar prijzen zijn uitsluitend voor optionele Support — software blijft gratis |
| "Try it free"-CTA | Prominent, overal | Niet aanwezig; installatie is de trial |
| Upgrade-druk | Structureel (Enterprise / Paid) | Nul; ons model sluit het uit |
| Commerciële mechaniek | Volledig (cart / checkout / billing) | Afwezig |

**Praktische impact:** onze site is **kleiner, eenvoudiger, minder commercieel** dan Odoo of Woo. Dat is geen tekortkoming, het is een feature van ons model. Waar hun ontwerpers moeten jongleren met trial-CTA's, pricing-vergelijking, upgrade-prompts en reviews, hebben onze ontwerpers één duidelijke taak: *laat zien wat de apps doen en stuur door naar de app store*.

---

## Van *upgrade-druk* naar *download-druk* — de kern-reframing

Als één inzicht uit deze analyse mee naar huis moet, is het dit: Odoo en WooCommerce werken met **upgrade/koop-druk** door hun hele UX heen. Alles leidt naar een aankoopbeslissing — trial starten, upgrade naar Enterprise, koop een extensie, betaal een abonnement. Hun CTA-psychologie draait om *"neem die stap, geef je geld uit, krijg meer"*.

Bij ons is die druk **download-druk**. Alles op onze site leidt naar één ding: **de app downloaden uit de Nextcloud app store**. Dat is een kosteloos, frictieloze actie. We zetten geen trial-urgency in, geen prijs-vergelijkingen, geen upgrade-nags. Gewoon: *"Hier is de app. Klik om te installeren. Klaar."*

**Concrete verschillen in CTA-psychologie:**

| | Odoo / Woo (upgrade-druk) | Conduction (download-druk) |
|---|---|---|
| Primaire verb | *"Try"* / *"Buy"* / *"Start"* / *"Upgrade"* | *"Installeer"* / *"Install"* / *"Download"* |
| Friction-niveau | Hoog (account aanmaken, betaling, trial-limiet) | Laag (één klik naar app store) |
| Urgentie-signalen | *"Save 20% this month"*, *"Free for 14 days"* | Geen — er is niks te haasten |
| Prijs-communicatie | Prominent op bijna elke pagina | Afwezig; software heeft geen prijs |
| Social proof | Omzet, klanten, revenue | Installs, gemeenten, forks |
| Eindpunt van elke flow | Aankoop of trial-signup | Doorklikken naar app store |

Deze reframing is niet alleen taalkundig. Ze bepaalt **hoe elke pagina eindigt**, wat "conversie" betekent, en welke UX-patronen we *niet* mogen kopiëren van Odoo en Woo (zelfs als ze visueel mooi zijn).

**Wat dat betekent voor layout-details:**

- Primary button zegt altijd *"Install from Nextcloud app store"* (of in EN dezelfde zin), nooit *"Get started"* of *"Sign up"*
- Geen floating/sticky CTA-bars met urgentie-tekst
- Geen exit-intent-popups met "last chance" boodschappen
- Geen pricing page in de hoofdnav (er is geen prijs)
- Secundaire CTA's zijn óf "Read docs", óf "View on GitHub" — altijd informatief, nooit commercieel

## Hoe ons gratis + Support-model de site fundamenteel anders maakt

### Odoo's feature-gating-model

Odoo **gebruikt** de Community-vs-Enterprise-split actief op bijna elke product-pagina. Je leest over een feature, je ziet in kleine letters "Enterprise only", en de subtiele suggestie is: upgrade. Dat is niet per se kwaadaardig — het is een legitiem verdienmodel — maar het **compliceert** de UX op elke pagina.

### WooCommerce's paid-extensions-model

WooCommerce is opener: core is gratis, extensies zijn grotendeels betaald. Elke extensie heeft een prijs. De marketplace is onmiskenbaar een commerciële plek.

### Ons model: altijd-gratis-software met optioneel Support via twee paden

Ons verhaal is eenvoudiger *én* unieker. **Elke app, elke feature, altijd gratis, altijd open source.** Geen feature-gate, geen access-voorwaarde.

**Support** (technisch: een SLA-contract) is een zekerheid-laag die op *twee* manieren verkrijgbaar is — een voor onze markt kenmerkend model dat we op de site expliciet moeten uitleggen:

- **Pad 1:** via een (officiële) Nextcloud-leverancier die de klant al heeft. Eén contract, één factuur, één aanspreekpartij — wij verrekenen achter de schermen via Nextcloud.
- **Pad 2:** rechtstreeks met ons, via een formulier in de admin-instellingen van de app zelf. Voor self-managed Nextcloud-omgevingen.

Volledige uitleg, pricing-tiers en pricing-tabel-structuur in [`support-model.md`](./support-model.md).

**Inhoud van Support (beide paden, zelfde inhoud):**

- Helpdesk-ondersteuning (reactief, contractuele responstijden)
- Proactieve ondersteuning op basis van telemetry (wij zien problemen voordat de klant erover belt, en waarschuwen actief)

Concreet wat dit betekent voor de site:

1. **Geen "Enterprise-only" of "Pro-only"-badges** ergens op een app- of solution-pagina. Alles wat je ziet is beschikbaar voor iedereen.
2. **Support-pagina mét volledige pricing, in de hoofdnavigatie.** Bezoekers die kosten willen weten moeten niet via een footer-link hoeven zoeken. De mitigatie zit in de pagina-content zelf: prominent *"Software is en blijft gratis. Onderstaande prijzen gelden alléén voor het Support-abonnement (facultatief)."*
3. **Support-pagina is informatief met pricing-tabel, maar géén bestelformulier.** Het bestelproces zit *niet* op onze site: pad 1 regelt de klant bij z'n eigen Nextcloud-leverancier, pad 2 via het formulier in de admin-instellingen van de geïnstalleerde app zelf. Onze site legt de twee paden uit en stuurt door — geen shopping-cart.
4. **Hero-tone is uitnodigend, niet sellend.** *"Installeer OpenCatalogi in 2 minuten"* werkt bij ons; *"Start your free trial"* niet (niets is een trial; het is gewoon de software).
5. **"Contact us" is niet de conversie.** Bij Odoo/Woo belandt elke doodlopende flow vaak op een contact-sales-formulier. Bij ons is "Contact us" een laatste-redmiddel, niet een funnel-doel. De conversie is *installeren*.
6. **Proof is gebruik, niet omzet.** Bij Odoo: "7 million users, 200 countries". Bij ons gebruik-georiënteerd: aantal installaties, aantal gemeenten, aantal forks op GitHub. Niet "omzet" of "klant-tevredenheid in sterren".

### Hoe Support te positioneren in copy

Niet als upsell. Als **bijproduct** van het open-source-verhaal. Ruwweg dit:

> *"Onze apps zijn altijd gratis. Je installeert ze uit de Nextcloud app store, je draait ze, je beheert ze. Klaar. Wil je meer zekerheid — helpdesk, proactieve monitoring, iemand die meekijkt bij problemen — dan hebben we Support. Je regelt het bij je Nextcloud-leverancier als je er een hebt; anders rechtstreeks met ons via de admin-instellingen in de app. Dat is hoe wij ons brood verdienen: niet door de software achter een paywall te zetten, maar door gemoedsrust te bieden voor wie dat nodig heeft."*

Dit is eerlijk, niet-bedreigend, legt het verdienmodel uit, erkent dat het een keuze is, en respecteert de intelligentie van de bezoeker.

### Support-pagina-structuur (samenvatting)

Zes secties, in deze volgorde:

1. Hero — *"Onze apps zijn altijd gratis. Support is optioneel."*
2. Wat zit in Support? (helpdesk + proactieve telemetry-ondersteuning)
3. Pricing-tabel (per app × per user × per jaar × 2 tiers, met prominente "software is gratis"-disclaimer)
4. Hoe vraag ik Support aan? (twee paden expliciet naast elkaar)
5. FAQ (6–8 vragen die in [`support-model.md`](./support-model.md) staan)
6. Contact-CTA (discreet einde van de pagina)

Voor de volledige uitwerking van elke sectie, inclusief pricing-structuur-keuzes per tier, zie [`support-model.md`](./support-model.md).

---

## Concrete ontwerp-beslissingen op basis van deze analyse

1. **Homepage-structuur:** 7 secties in deze volgorde:
   1. Hero (headline + app-store-CTA + screenshot)
   2. Waarde-teasers (4 blokken: "Open source", "Eigen Nextcloud", "Geen vendor lock-in", "NL Design")
   3. Apps-grid (6–8 featured core apps met tagline)
   4. Solutions-teasers (3–4 top solutions)
   5. Stats-strip (GitHub-stars, gemeenten, installed-counts)
   6. Support-teaser (discreet, één strip linkend naar /support)
   7. Footer

2. **Apps-catalogus:** filter-sidebar + grid, facets = categorie × status × Nextcloud-versie × NLDS-compliance. Sortering: Featured / Alphabetical / Newest.

3. **App-detail-pagina:** hero + sticky intra-page-nav + 4–6 alternerende feature-blokken + integration-strip + technische-metadata-sidebar + CTA-herhaling. **Geen** reviews-tab.

4. **Solution-pagina:** het template uit [`solution-woo.md`](./solution-woo.md) staat al goed — dat volgt precies het "problem → approach → app-stack → FAQ"-patroon dat Odoo's industry-pagina's ook gebruiken.

5. **Support-pagina:** één pagina, in de hoofdnavigatie. Structuur: Hero ("Apps zijn gratis, Support is optioneel") / Wat zit in Support? / Pricing-tabel (per app × per user × per jaar × 2 tiers) / Hoe vraag ik 'm aan? (twee paden) / FAQ / Contact-CTA. Prijzen staan op de pagina mét prominente "software is gratis"-disclaimer. Zie [`support-model.md`](./support-model.md) voor de volledige invulling.

6. **Services-pagina:** zoals in §6.7 van de brief — discreet in footer, niet in hoofdnav.

7. **Navigation:** Apps / Solutions / Support / About / Docs (extern) / GitHub (extern) in header. Services, Contact, Privacy, Legal, Taalwisselaar in footer.

8. **Mega-menu voor Apps:** alleen als we er visueel iets aan toevoegen (preview-kaarten met screenshot). Als het een platte link-lijst wordt, hoeft het geen mega-menu te zijn.

---

## Wat deze analyse **niet** is

- Geen volledige reverse-engineering van hun CSS/tech-stack. Dat is niet nodig en bovendien grotendeels achterhaald — Odoo en WooCommerce hebben zelf in-house design-systems die niet publiek gedocumenteerd zijn.
- Geen kwantitatieve analyse (A/B-tests, conversie-cijfers). Die data is intern.
- Geen update-service. Als Odoo of WooCommerce hun site herzien, veroudert deze analyse. Bij een major redesign (>1x per 2 jaar) herzien we dit document.

---

## Appendix: losse observaties die we mogelijk willen gebruiken

- **Odoo's app-icon-stijl** — elk app-icon is een custom SVG in een soft-gradient, niet alleen een symbool. Wij gebruiken hexagon-wrappers + één-kleur-icoon; consistenter en goedkoper om te onderhouden, maar visueel minder rijk. Acceptabel trade-off.
- **WooCommerce's verified-badge-systeem** — extensies van verifiable vendors krijgen een badge. Bij ons is dit irrelevant (één vendor = Conduction) maar als we ooit community-apps toelaten, overwegen we een "Conduction Certified"-badge.
- **Beiden gebruiken geen dark mode by default** — light-themed marketing-site. Onze scope-A zegt ook: geen dark mode voor nu. Dat bevestigt dat we daar geen tijd aan moeten verspillen.
- **Beiden investeren zwaar in customer-stories.** Wij niet — nog. Op de roadmap zetten voor ná launch.
