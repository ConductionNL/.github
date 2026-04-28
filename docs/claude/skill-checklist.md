# Skill Checklist

Quick validation checklist before adding or reviewing a Claude Code skill. Organized by [maturity level](writing-skills.md#skill-maturity-levels).

---

## L1-L2 (minimum for any skill)

- [ ] Folder name matches `name` in frontmatter and the slash command
- [ ] `description` is action-oriented, third-person, under 250 characters, with specific trigger terms
- [ ] Steps are numbered and self-contained
- [ ] Guardrails define what the skill must NOT do
- [ ] Destructive actions have explicit confirmation prompts
- [ ] `SKILL.md` is under 500 lines — large blocks extracted to subfolders
- [ ] All subfolder links use relative paths
- [ ] `SKILL.md` reads coherently top to bottom without opening subfolder files

## L3 (recommended for all skills)

- [ ] Uses common patterns consistently (model guard, AskUserQuestion, quality checks)
- [ ] Has `examples/` if the skill produces structured output
- [ ] References standards documents where applicable

## L4 (recommended for business-critical skills)

- [ ] Contains business-specific `references/` (standards, architecture, ADRs)
- [ ] Uses project-specific templates and terminology
- [ ] Output matches team expectations without manual correction

## L5+ (recommended for frequently-used skills)

- [ ] Has 3+ eval scenarios in `evals/`
- [ ] Baseline measurement documented (output without skill)
- [ ] Description trigger-tested (10 should + 10 should-not queries)
- [ ] PHP/Python quality checks triggered after code changes (if applicable)

## L6+ (recommended for skills that run often and evolve)

- [ ] Has `learnings.md` with dated, atomic entries
- [ ] SKILL.md includes "capture learnings" step
- [ ] Consolidation process defined (trigger at ~80-100 entries)

## L7 (for workflow and orchestration skills)

- [ ] Part of a defined workflow chain with explicit handoff
- [ ] Spawns subagents or is spawned by orchestrator
- [ ] Tested end-to-end as part of the full chain
