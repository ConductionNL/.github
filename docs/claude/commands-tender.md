# Tender & Ecosystem Intelligence Commands

These commands support the competitive analysis and ecosystem gap-finding workflow. They operate on the `concurrentie-analyse/intelligence.db` SQLite database and require the database to exist before running.

---

### `/tender-scan`

**Phase:** Intelligence Gathering

Scrape TenderNed for new tenders, import them into SQLite, and classify unclassified tenders by software category using a local Qwen model.

**Usage:**
```
/tender-scan
```

**What it does:**
1. Runs `concurrentie-analyse/tenders/scrape_tenderned.py` to fetch fresh data
2. Imports new tenders into the intelligence database
3. Classifies unclassified tenders using Qwen via `localhost:11434`
4. Reports new tenders found, classified, and any new gaps detected

**Requires:** Local Qwen model running on Ollama (`http://localhost:11434`)

---

### `/tender-status`

**Phase:** Intelligence Monitoring

Show a dashboard of the tender intelligence database — totals by source, category, status, gaps, and recent activity.

**Usage:**
```
/tender-status
```

**What it does:**
- Queries `concurrentie-analyse/intelligence.db` for live stats
- Shows tenders by source, status, and category (top 15)
- Highlights categories with Conduction coverage vs gaps
- Shows top integration systems and ecosystem gaps

**Model:** Checked at run time when invoked standalone — stops if on Opus (no reasoning needed, wastes quota), warns if on Sonnet and offers to switch. **Haiku** is the right fit for this task. Model check is skipped when this skill is called from within another skill.

---

### `/tender-gap-report`

**Phase:** Gap Analysis

Generate a gap analysis report — software categories that appear in government tenders but have no Conduction product.

**Usage:**
```
/tender-gap-report
```

**What it does:**
1. Queries the database for categories with tenders but no `conduction_product`
2. Generates a markdown report at `concurrentie-analyse/reports/gap-report-{date}.md`
3. Includes top 5 gaps with tender details, organisations, and key requirements
4. Cross-references with `application-roadmap.md` to flag already-tracked gaps
5. Recommends which gaps to investigate first

---

### `/ecosystem-investigate <category>`

**Phase:** Competitive Research

Deep-dive research into a software category — find and analyze open-source competitors using GitHub, G2, Capterra, AlternativeTo, and TEC.

**Usage:**
```
/ecosystem-investigate bookkeeping
```

**What it does:**
1. Loads category context and related tenders from the intelligence database
2. Uses the browser pool (browser-1 through browser-5) to scrape 5-10 competitors from multiple source types
3. Creates competitor profiles in `concurrentie-analyse/{category}/{competitor-slug}/`
4. Inserts competitors and feature data into the database with provenance tracking
5. Presents a comparison table and recommendation for Nextcloud ecosystem fit

**Model:** Checked at run time — stops if on Haiku. Asks which model to use and explains how to switch if the choice differs from the active model. **Sonnet** for most categories. **Opus** for high-stakes or complex categories where strategic depth matters.

---

### `/ecosystem-propose-app <category>`

**Phase:** Product Planning

Generate a full app proposal for a software category gap, using tender requirements and competitor research as input.

**Usage:**
```
/ecosystem-propose-app bookkeeping
```

**What it does:**
1. Gathers all tenders, requirements, competitors, and integrations for the category
2. Generates a structured proposal following the template in `concurrentie-analyse/application-roadmap.md`
3. Appends the proposal to `application-roadmap.md`
4. Inserts the proposal into the `app_proposals` database table
5. Optionally bootstraps the app with `/app-create`

**Model:** Checked at run time — stops if on Haiku. Asks which model to use and explains how to switch if the choice differs from the active model. **Sonnet** for most proposals. **Opus** for high-stakes proposals where architectural fit and market analysis need extra depth.

---

### `/intelligence-update [source]`

**Phase:** Intelligence Maintenance

Pull latest data from external sources into the intelligence database. Syncs sources that are past their scheduled interval.

**Usage:**
```
/intelligence-update              # sync all sources that are due
/intelligence-update all          # force sync every source
/intelligence-update wikidata-software  # sync one specific source
```

**Sources and intervals:**

| Source | Interval |
|--------|----------|
| `tenderned` | 24h |
| `wikidata-software` | 7 days |
| `wikipedia-comparisons` | 7 days |
| `awesome-selfhosted` | 7 days |
| `github-issues` | 7 days |
| `dpg-registry` | 7 days |
| `developers-italia` | 7 days |
| `gemma-release` | yearly |

**What it does:**
1. Checks `source_syncs` table for overdue sources
2. Runs `concurrentie-analyse/scripts/sync/sync_{source}.py` for each
3. Updates sync status, records count, and error messages
4. Displays a summary table of all sources with their sync status

**Model:** Checked at run time when invoked standalone — stops if on Opus (no reasoning needed, wastes quota), warns if on Sonnet and offers to switch. **Haiku** is the right fit for this task. Model check is skipped when this skill is called from within another skill.

---

## Tender Intelligence Workflow

```
/tender-scan              (fetch & classify new tenders)
       │
       ▼
/tender-status            (review dashboard)
       │
       ▼
/tender-gap-report        (identify gaps)
       │
       ▼
/ecosystem-investigate    (research competitors for top gap)
       │
       ▼
/ecosystem-propose-app    (generate app proposal)
       │
       ▼
/app-design          (design the new app)
```

**Keep data fresh:** Run `/intelligence-update` weekly and `/tender-scan` daily to keep the database current.
