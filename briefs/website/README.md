# briefs/website/ — content appendix voor de website-brief

Content-bestanden die horen bij [../website.md](../website.md). Deze bestanden vullen concrete gaten uit de one-shot-review met data die rechtstreeks uit onze competitive-intelligence DB komt (`concurrentie-analyse/intelligence.db`), zodat de designer niet met placeholders of verzonnen copy hoeft te werken.

## Bestanden

| Bestand | Vult gap | Inhoud |
|---|---|---|
| [`app-taglines.md`](./app-taglines.md) | #17 | MKB-directe tagline (NL + EN) per core app, gekalibreerd op top-features uit de DB. Inclusief review-checklist en verbannen-lijst. |
| [`solution-woo.md`](./solution-woo.md) | #18 | Volledige WOO-solution-pagina als **template** voor alle andere solution-pagina's. Authentieke stakeholder-taal uit 1.031 NL tenders en 5.992 requirements. Dekt hero, probleem, aanpak, app-stack, FAQ, SEO-metadata. |
| [`tone-samples.md`](./tone-samples.md) | #16 (deel) | NL tone-calibratie: drie registers (tender-/systeem-/user-story-taal), rewrite-recepten naar MKB-direct, 7 gouden regels, verbannen-lijst. |
| [`icon-library.md`](./icon-library.md) | #12 (deel) | Afwegingskader + aanbeveling (Lucide). Kandidaten vergeleken op licentie, stijl, peer-group-adoptie, bundle. Inclusief expliciete "Waarom niet Font Awesome?"-sectie. |
| [`platform-benchmarks.md`](./platform-benchmarks.md) | — (aanvulling op #20) | Uitgebreide analyse van **Odoo** en **WooCommerce** als app-platform-referenties. Per platform: IA, homepage, catalogus-UX, detail-pagina-template, pricing/paid-patronen, community-model. Eindigt met 7 concrete ontwerp-beslissingen voor ons + reframing "upgrade-druk → download-druk" en analyse van hoe ons gratis + SLA-model de IA fundamenteel anders maakt. |
| [`support-model.md`](./support-model.md) | — (verdienmodel) | Het Conduction Support-model in detail: wat er concreet in Support zit (helpdesk + proactieve telemetry-ondersteuning), de twee aanvraagpaden (via Nextcloud-leverancier of rechtstreeks via app-admin-formulier), **pricing-structuur** (per app × per user × per jaar × 2 tiers Standard/Premium met placeholder-waardes ter bevestiging), en wat dat betekent voor de Support-pagina-structuur op de website. Naam-keuze "Support" over "SLA": toegankelijker voor klanten; SLA blijft de technische term voor het onderliggende contract. |
| [`services-model.md`](./services-model.md) | — (verdienmodel) | Het Conduction Services-model: volledige tarievenkaart voor projectmatig werk — Development €125/uur, Consultancy €150/uur, strippenkaart €15K met 10% korting, fysieke training €1.000–€1.200 per dagdeel (8u gefactureerd per 4u lestijd), online training gratis, certificering €150–€500 per certificaat (indicatief). Inclusief strippenkaart-mechaniek, trainings-varianten, en Services-pagina-structuur. |
| [`visual-motifs.md`](./visual-motifs.md) | — (visueel systeem) | Drie visuele beslissingen: (1) hexagon als systematisch motief (catalogus van UI-toepassingen + regel "hex voor accenten, niet voor containers"), (2) per-sectie-treatments met opties en aanbevelingen voor homepage-secties, app-detail, solution-landing, Support, Services, About, 404, (3) illustratie-stijl: 7 named-style-kandidaten (Open Peeps, Humaaans, Storyset Line, Blush, Drawkit, Ouch, Streamline) ter bevestiging + master-briefing-tekst voor illustrators/AI. |

## Wat hier nog bij komt (later)

Deze map groeit mee terwijl we verder ontwerpen:

- `design/` — statische HTML+CSS mocks per pagina-type (fase 1 van de implementatie-aanpak; zie [../website.md §15](../website.md))
- `solution-register.md`, `solution-zaakafhandeling.md`, … — één per toekomstige solution, gebouwd op hetzelfde template als `solution-woo.md`
- `copy-library.md` — herbruikbare zinsfragmenten (CTA-labels, error-messages, empty-states, microcopy) in NL + EN
- `photography-illustration-refs.md` — visuele referenties voor illustratie-stijl zodra die gekozen is (gap #13)

## Relatie tot de foundation-documenten

Deze bestanden zijn **surface-specifiek** (website). Als een inzicht hier company-wide blijkt, verplaatst het naar:

- [`../../BRAND.md`](../../BRAND.md) — als het gaat over wie we zijn of hoe we naar de wereld spreken
- [`../../DESIGN.md`](../../DESIGN.md) — als het gaat over algemene ontwerp-keuzes of tone-richtlijnen
- [`../../brand/tokens.json`](../../brand/tokens.json) — als het gaat over design-tokens

De brief en deze appendix duren zolang als de website-overhaul duurt; de foundation-documenten blijven bestaan.
