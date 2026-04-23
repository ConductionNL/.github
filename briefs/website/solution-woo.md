# Solution: WOO-compliance (pilot template)

Eén volledige solution-pagina als **template** voor alle andere solution-pagina's. De inhoud is geen placeholder — ze komt rechtstreeks uit onze tender-intelligence en geeft een designer genoeg om de solution-landing-page-template te valideren in één shot.

**Bron-samenvatting:**

- **1.031 NL-tenders** in onze DB verwijzen naar *Wet open overheid* / Woo / openbaarmaking
- **5.992 tender-requirements** noemen expliciet Woo/openbaarmaking
- Representatieve inkopers o.a. Gemeente Rotterdam, Gemeente Tilburg, Gemeente Amersfoort, Gemeente Dordrecht, Gemeente Den Haag, Gemeente Oldambt, De Connectie (Arnhem/Rheden/Renkum), Provincie Limburg
- Gangbare termen uit de tender-teksten: *publicatieplatform*, *publicatievoorziening*, *Woo-index (harvester)*, *informatiehuishouding*, *actief openbaar maken*, *Woo-coördinator*, *anonimisering*
- Rechtsbasis genoemd in requirements: *artikel 5.1 Wet open overheid* (actieve openbaarmakings-categorieën)

Hieronder staat de volledige content — hero, probleem-uitleg, aanpak, app-stack, FAQ, CTA — in de vorm waarin een designer hem één-op-één kan ingieten in een solution-landing-page-mock. NL primair, EN secundair. Elke alinea-bron is gelabeld met `[tender]`, `[requirement]`, `[standard]` of `[Conduction]`.

---

## Hero

**H1 (NL):** *Voldoen aan de Wet open overheid — zonder dure publicatietool apart te kopen*

**H1 (EN):** *Comply with the Dutch Open Government Act — without buying a separate publication tool*

**Lead (NL):** *De Woo vraagt publieke organisaties om informatie actief openbaar te maken. Dat lukt alleen als publicatie, anonimisering en archivering naadloos samenwerken met je bronsystemen. Conduction-apps leveren die keten, open source en op je eigen Nextcloud.*

**Lead (EN):** *The Dutch Open Government Act requires public organisations to actively publish information. That only works when publication, anonymisation and archiving integrate seamlessly with your source systems. Conduction apps deliver that chain, open source and on your own Nextcloud.*

**Primaire CTA:** *"See the stack"* → scrolt naar app-stack-sectie
**Secundaire CTA:** *"Ask a Conduction engineer"* → contact (subtle, geen hoofdCTA)

---

## Het probleem — wat is de Woo, en waarom knelt het?

**Authentieke stakeholder-taal uit tenders (gecomprimeerd):**

> *"We moeten een publicatievoorziening maken met krachtige zoektechnologie die is verbonden met onze bronsystemen, zodat informatie van binnen naar buiten kan en voor de inwoner vindbaar is."* — [tender] Gemeente Tilburg, *Publicatievoorziening WOO*
>
> *"De openbaarmaking moet gebeuren zonder export van documenten naar het publicatieplatform; opslag en vernietiging van te publiceren documenten blijft in de bron plaatsvinden."* — [requirement] uit meerdere NL-tenders
>
> *"We zoeken ondersteuning voor het integrale Woo-proces."* — [tender] De Connectie (gemeentes Arnhem, Rheden, Renkum)

**Wat dit betekent voor een gemeente of MKB-organisatie (MKB-taal):**

De Wet open overheid — in jargon "Woo", in klare taal "de wet die zegt: publiceer je informatie proactief" — is sinds 1 mei 2022 van kracht. In plaats van wachten op een verzoek moet je bepaalde categorieën documenten uit eigener beweging publiceren: raadsinformatie, besluiten, klachten, subsidies, vergunningen, convenanten, en meer (artikel 5.1 Wet open overheid, 11 verplichte categorieën).

Dat klinkt simpel tot je gaat bouwen. Dan loop je tegen vier realiteiten aan:

1. **De informatie zit in verschillende systemen** — zaaksysteem, DMS, raadsinformatie­platform, CRM, soms zelfs spreadsheets. Er is geen "centrale plek".
2. **Publicatie vraagt anonimisering.** Persoonsgegevens moeten eruit, BSN's weg, soms hele passages. Dat moet betrouwbaar, aantoonbaar, en reversible voor interne audit.
3. **Zoek moet werken.** Zonder een goede zoekmachine is je publicatie theoretisch openbaar maar praktisch onvindbaar. De landelijke Woo-index (harvester) moet je pagina's kunnen ophalen.
4. **Dubbele opslag is een risico.** Een kopie in een publicatieplatform betekent: twee waarheden, synchronisatie-fouten, en vernietigings-termijnen die uit de pas lopen met de bron.

De markt biedt hiervoor een rij proprietary *publicatietools* — vaak aparte SaaS-producten die je data uit je bronsystemen *exporteert*. Dat werkt, maar leidt tot precies die vier problemen.

## De aanpak — *source-of-truth publication*

Conduction kiest een andere route, conform het Common Ground-uitgangspunt: **publiceer vanuit de bron, niet uit een kopie**. De publicatielaag is dun; de bronsystemen blijven de gezaghebbende opslag. Anonimisering en publicatie gebeuren als "view" op de bron, niet als export.

Concreet betekent dat voor je organisatie:

- **Je bronsystemen** (zaaksysteem, DMS, raadsinformatie, register) blijven waar ze zijn en behouden hun eigen vernietigings-termijnen
- **De publicatielaag** zoekt, anonimiseert en toont — zonder de documenten te kopiëren
- **De Woo-index** haalt metadata op via een gestandaardiseerde harvester-route
- **De inwoner** zoekt in één interface dat over al je systemen heen werkt

Dat past bij de NL-standaarden (Common Ground, NL API Strategie, NL Design System) en levert één voordeel dat elke andere tool lastig kan claimen: **één bron voor elk document, ook na publicatie**.

## De app-stack — welke apps doen wat

Om een Woo-compliance-keten te draaien op je Nextcloud, koppel je vier Conduction-apps.

| Rol in de keten | App | Wat de app doet |
|---|---|---|
| **1. Registratie & bron-opslag** | [OpenRegister](../../../apps/openregister) | Gestructureerde objecten en documenten, één datastore voor registraties. |
| **2. Catalogus & publicatie** | [OpenCatalogi](../../../apps/opencatalogi) | Federated catalogus met krachtige zoekmachine; publieke vindbaarheid; harvester-koppeling voor de Woo-index. |
| **3. Integratie met bestaande systemen** | [OpenConnector](../../../apps/openconnector) | API-gateway die je zaaksysteem, DMS, raadsinformatie en andere bronnen koppelt aan OpenRegister zonder dubbele opslag. |
| **4. Document-generatie & anonimisering** | [DocuDesk](../../../apps/docudesk) | Sjablonen, anonimiseren, audit-trail voor publicatie-beslissingen door de Woo-coördinator. |

**Optioneel:** [MyDash](../../../apps/mydash) voor een Woo-dashboard (wachtrij van te publiceren documenten, doorlooptijd, gepubliceerd-per-maand). [NL Design](../../../apps/nldesign) voor een publicatie-interface in de NL Design-huisstijl.

**CTA:** *Install all four apps from the Nextcloud app store* → linkt naar app-catalogus gefilterd op `solution=woo`

## Frequently Asked Questions

**1. Moeten we alles tegelijk installeren?**
Nee. Begin met OpenRegister en OpenCatalogi — dat dekt publicatie en vindbaarheid. Voeg OpenConnector toe zodra je bestaande systemen wilt koppelen. DocuDesk is handig vanaf het moment dat anonimisering structureel wordt. [Conduction]

**2. Vervangen deze apps ons huidige zaaksysteem?**
Nee. De aanpak is juist om je zaaksysteem te behouden als bron en er vanuit te publiceren via OpenConnector. Zie de Common Ground-referentie-architectuur. [Conduction]

**3. Wat met de landelijke Woo-index / open.overheid.nl?**
OpenCatalogi publiceert metadata en documenten conform de harvester-specificaties, zodat de landelijke Woo-index je pagina's kan indexeren. "De door de Oplossing gebruikte webpagina en achterliggende URL's moeten gevonden kunnen worden door de Woo-index (harvester)." [requirement]

**4. Hoe zit het met anonimisering van persoonsgegevens?**
DocuDesk biedt anonimiseer-functionaliteit met audit-trail, zodat elke redactie aantoonbaar en reversible is voor interne controle. "De Oplossing biedt de mogelijkheid om documenten door de Woo-coördinator te laten controleren op inhoud en anonimisering voor hun publicatie." [requirement]

**5. Welke van de 11 Woo-categorieën uit artikel 5.1 worden ondersteund?**
Alle 11 categorieën zijn qua *structuur* ondersteund (wetten en algemeen verbindende voorschriften, organisatiegegevens, raadsstukken, convenanten, jaarplannen en -verslagen, subsidies, klachten, beschikkingen, onderzoeken, beslissingen op Woo-verzoeken, wetenschappelijke informatie). De precieze implementatie hangt af van welke bronsystemen je aan OpenConnector hangt.

**6. Is deze stack Common Ground-conform?**
Ja. *"The Contracting Authority is open to an implementation of WOO document delivery that aligns with Common Ground architecture, serving documents from the source."* — exact waar Conduction op mikt. [requirement]

**7. Welke licentie?**
Alle vier apps zijn EUPL-1.2 open source. Je host ze zelf op je Nextcloud, er is geen per-user of per-document prijs.

## Proof / referenties

*(te vullen zodra klant-toestemming er is — placeholder, in de mock kunnen we twee fictieve kwoten tonen om lay-out te valideren)*

- *"Sinds we OpenCatalogi draaien is de doorlooptijd van actieve publicatie gehalveerd."* — IT-lead, fictief-gemeente, placeholder
- *"De Woo-index harvest onze pagina's nu automatisch, we hoeven niks meer handmatig te publiceren."* — Woo-coördinator, fictief-gemeente, placeholder

## Call-to-action (pagina-slot)

**Primair:** *"Start met de Woo-stack — installeer vanuit de Nextcloud app store"*
→ Links naar: OpenRegister, OpenCatalogi, OpenConnector, DocuDesk

**Secundair:** *"Stel een vraag aan een Conduction engineer"* → contactformulier

---

## SEO-metadata voor deze pagina

- **Title-tag (NL):** *Wet open overheid (Woo) compliance met open source — Conduction*
- **Title-tag (EN):** *Dutch Open Government Act (WOO) compliance with open source — Conduction*
- **Meta-description (NL):** *Woo-compliant publiceren vanuit de bron, zonder kopieën of dure publicatietool. Open source apps op je eigen Nextcloud.*
- **Meta-description (EN):** *Publish under the Dutch Open Government Act directly from source systems, without copies or expensive SaaS. Open-source apps on your Nextcloud.*
- **Keywords (NL primair):** Woo-compliance, Wet open overheid, publicatievoorziening, publicatietool Woo, Woo-coördinator, actieve openbaarmaking, Common Ground Woo, Woo-index, anonimisering documenten
- **Keywords (EN secundair):** Dutch Open Government Act, WOO compliance, open source publication platform, government transparency software
- **Structured data:** `SoftwareApplication` per app in de stack; `FAQPage` voor de FAQ-sectie; `Article` voor de problem-uitleg
- **Canonical + hreflang:** NL en EN versies wijzen naar elkaar; hreflang `nl` en `en` plus `x-default=nl`

---

## Open punten voor de solution-pagina

- Screenshots per app in de stack (nog te produceren; zie gap #15 in de one-shot-review)
- Stack-diagram als visual — moet nog als illustratie-template ontworpen worden (zie design-fase §15 in [../website.md](../website.md))
- Getallen ("halvering doorlooptijd" etc.) zijn nu placeholders — vervangen zodra er klant-data is
- Juridische review: de tekst claimt compliance-mogelijkheid, geen compliance-garantie. Voor launch laten beoordelen door juridisch adviseur.

---

## Wat deze pagina als template laat zien

Dit zijn de **verplichte secties** voor elke solution-landing-pagina (template voor de andere solutions — organisatieregister, zaakafhandeling, softwarecatalogus, Common Ground):

1. Hero (H1, lead, primaire CTA, secundaire CTA)
2. Probleem-sectie met authentieke stakeholder-quotes
3. Aanpak-sectie (wat onderscheidt onze aanpak?)
4. App-stack-tabel met rol-per-app
5. FAQ (min. 5, max. 8 vragen)
6. Proof / referenties (placeholder waar klant-quotes nog missen)
7. Call-to-action-slot (primair + secundair)
8. SEO-metadata (title, meta-description, keywords, structured data, canonical/hreflang)

Elke andere solution-pagina volgt deze structuur. Alleen de inhoud wisselt.
