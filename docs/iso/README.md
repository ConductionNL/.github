# ISO Compliance Documentation

This folder maps the Conduction engineering pipeline to ISO / IEC standards so that we can see, clause by clause, what we already meet, what we partially meet, and what we don't cover yet. Gaps are a first-class output of these documents — the intent is to close them, not to hide them.

## Current scope

| File | Standard | Topic | Status |
|------|----------|-------|--------|
| [code.md](./code.md) | ISO 9001:2015 (+ ISO/IEC 90003 software interpretation) | Code-quality Quality Management System | Active |

## Adjacent standards we deal with (not covered here yet)

| Standard | Topic | Where it lives today |
|----------|-------|----------------------|
| ISO 27001 | Information security management | Handled via hosting partner Cyso (ISAE 3402 Type II). Conduction does not hold an independent certificate. |
| ISAE 3402 | Service-organization controls | Inherited from Cyso. |
| BIO (Baseline Informatiebeveiliging Overheid) | Dutch government baseline | **Not yet implemented.** Planned. |
| DigiD assessment | Dutch citizen auth | **Out of scope** — Conduction apps do not authenticate citizens directly. |
| NEN 7510 | Healthcare information security | **Out of scope** unless/until we ship healthcare deployments. |

**Note for the future `security.md` (ISO 27001 track):** during the Specter audit we observed a `gho_`-prefixed OAuth token embedded in `concurrentie-analyse/.git/config`. Residual risk is bounded — short TTL, private repo — so no immediate action needed. Worth remembering as an example of the kind of pattern a 27001 control would systematize (credential helpers by default; no baked-in tokens in config files, even short-lived ones).

These may earn their own files in this folder later (`security.md` for 27001, `bio.md`, etc.). For now `code.md` is the only resident — the rest is tracked in [reference_conduction-roadmap.md](../ROADMAP.md) and in the memory index under *Tender Analysis & Compliance*.

## How to read these documents

Each clause of the target standard gets a small block:

1. **Clause ID + title** — exactly as published in the standard.
2. **What the standard asks for** — paraphrased in one or two sentences. We do not reproduce the ISO text verbatim (copyright); we describe the requirement.
3. **Our implementation** — concrete artefacts: file paths, tools, ADR numbers, workflow steps.
4. **Coverage** — one of:
   - **Full** — a reasonable auditor would accept this.
   - **Partial** — we do the thing, but not systematically or not documented.
   - **None** — we do not yet meet this clause.
   - **N/A** — the clause does not apply to software engineering as we practise it (e.g. calibration of physical measuring equipment).
5. **Gap & how to close it** — only present when coverage is not *Full*. A concrete next step, not a vague aspiration.

## Why ISO 9001 first

The code-quality pipeline is the most mature part of the business. It is also the easiest to evidence: every claim can be pointed at a file in this monorepo. Starting here lets us practise the format before we take on the harder standards (BIO, 27001 internally) where evidence is spread across infrastructure, policies, and third parties.

## Keeping these documents honest

The mapping is only useful if it reflects reality. Rules:

- **No aspirational claims.** If an ADR exists but is not enforced, mark the clause *Partial* and describe the enforcement gap.
- **Cite, don't paraphrase.** Every "our implementation" line names a file path, ADR, workflow job, or skill. If you can't cite it, it doesn't count.
- **Review cadence.** Revisit these docs whenever the pipeline changes materially — a new Hydra gate, a new ADR, a change in branch-protection rulesets. Don't let them drift.
