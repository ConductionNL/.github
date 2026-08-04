# Skill Level Sources

External sources grounding the L1–L7 skill maturity framework defined in
[writing-skills.md](./writing-skills.md). The framework is **not** our
invention — it adapts a community framing, is validated against Anthropic's
official guidance, and echoes the shape of long-established human-competence
and process-maturity models. This page records where each idea comes from,
what each source is good for, and — just as important — which
frequently-suggested sources we assessed and deliberately **excluded**.

All links verified 2026-07-26.

---

## 1. Direct ancestry — agent skills and their levels

The sources the L1–L7 framework is actually built from.

| Source | What it is | Grounds |
| --- | --- | --- |
| Simon Scrapes, ["Every Level of Claude Code Skills in 27 mins"](https://www.youtube.com/watch?v=-u_igSQHAIo) (YouTube, 19 Mar 2026) | The direct ancestor of our 7-level framing | The L1–L7 ladder itself |
| Anthropic, ["Skill authoring best practices"](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices) | Official authoring guidance: conciseness, degrees of freedom, descriptions/triggering, progressive disclosure, "build evaluations first" | L1, L2, L3, L5 |
| [Agent Skills open standard](https://agentskills.io/specification) — published by Anthropic (18 Dec 2025), aligned with the Agentic AI Foundation (Linux Foundation; long-term governance not yet formally settled); adopted by Microsoft, OpenAI, Atlassian, Figma, Cursor, GitHub | The specification of what a skill *is* (SKILL.md format, frontmatter, progressive disclosure tiers, `skills-ref validate`) | L1 |
| Barry Zhang & Mahesh Murag (Anthropic), ["Don't Build Agents, Build Skills Instead"](https://www.youtube.com/watch?v=CEvIs9y1uog) (AI Engineer, late 2025) | The thesis: agents lack expertise; skills are composable procedural knowledge loaded at runtime | The overall premise |
| Anthropic, ["Improving skill-creator: Test, measure, and refine Agent Skills"](https://claude.com/blog/improving-skill-creator-test-measure-and-refine-agent-skills) | skill-creator's Create/Eval/Improve/Benchmark modes; with-skill vs without-skill A/B benchmarking; pass-rate/latency/token metrics | L5 (see [skill-evals.md](./skill-evals.md)) |
| MindStudio, ["How to Build a Learnings Loop for Claude Code Skills That Self-Improve"](https://mindstudio.ai/blog/how-to-build-learnings-loop-claude-code-skills) (19 Mar 2026) | The persistent `learnings.md` feedback mechanism | L6 |
| Community implementations: [claude-reflect-system](https://github.com/haddock-development/claude-reflect-system), [claude-meta](https://github.com/aviadr1/claude-meta), [turbo](https://github.com/tobihagemann/turbo), [self-learning-skills](https://github.com/Kulaxyz/self-learning-skills) | Working learnings-loop variants (correction capture, confidence tracking, golden-path persistence) | L6 |

> **Key fact:** there is **no official Anthropic concept of "skill levels"** —
> neither the Claude Code docs nor the Agent Skills standard define maturity
> tiers. Anthropic provides the *machinery* (eval tooling, hooks, dynamic
> context injection); the leveling is a community/Conduction construct.

---

## 2. Human skill-level frameworks — the ladder's ancestry

Established frameworks that grade **people**. They legitimize the "numbered
levels of skill" shape and give us shared vocabulary with clients, but none
of them grades an *artifact* the way L1–L7 does.

| Source | Levels | Mapping onto L1–L7 |
| --- | --- | --- |
| [SFIA 9](https://sfia-online.org/en/sfia-9/sfia-9) (SFIA Foundation, Oct 2024) — Skills Framework for the Information Age | 7 levels of responsibility: 1 Follow → 7 Set strategy | Same ladder shape and count, but measures human autonomy/influence. SFIA 9 explicitly covers AI skills and even offers [guidance on using its levels to decide which tasks to assign to AI](https://sfia-online.org/en/sfia-9/sfia-9-release-notes/ai-skills-framework/using-sfia-levels-of-responsibility-to-analyse-what-tasks-responsibilities-to-assign-to-ai) |
| [Dreyfus model of skill acquisition](https://apps.dtic.mil/sti/tr/pdf/ADA084551.pdf) — Dreyfus & Dreyfus, UC Berkeley ORC-80-2 (1980) | 5 stages, canonically Novice → Advanced Beginner → Competent → Proficient → Expert (the 1980 paper uses novice → competence → proficiency → expertise → mastery) | Rule-following → intuition in a learner ≈ L1 (follow anatomy) → L6 (self-improvement), for human cognition |
| [European e-Competence Framework (e-CF)](https://itprofessionalism.org/professionalism/e-competence-framework/), EN 16234-1:2019 (CEN TC 428) | 41 competences × 5 proficiency levels e-1…e-5, aligned to EQF 3–8 | Closest human analogue to "one skill, graded levels" — a proficiency-per-competence matrix |
| [KWIV — Kwaliteitsraamwerk Informatievoorziening](https://www.functiegebouwrijksoverheid.nl/kwaliteitsraamwerken/kwaliteitsraamwerk-informatievoorziening) 4.0 (Rijksoverheid, Dec 2023) | ~61 kwaliteitenprofielen for government IV/IT roles, [explicitly built on e-CF](https://www.nen.nl/nieuws/ict/rijksoverheid-implementeert-e-competence-framework-via-eigen-kwaliteitsraamwerk-/) | **The Dutch-government hook**: the Rijksoverheid already runs its IT workforce on e-CF levels — a skill ladder that name-checks e-CF/KWIV speaks our clients' language |
| Bloom's taxonomy (revised) — Anderson & Krathwohl (2001), *A Taxonomy for Learning, Teaching, and Assessing* | 6 cognitive levels: Remember → … → Evaluate → Create, plus a knowledge dimension | Evaluate → Create maps onto L5 → L6/L7; "metacognitive knowledge" is a good frame for the L6 learnings loop |

---

## 3. Maturity models — levels applied to capability, not people

The conceptually closest ancestry: maturity of a **process or capability**,
which is what L1–L7 grades for a skill artifact + its improvement process.

| Source | Levels | Mapping onto L1–L7 |
| --- | --- | --- |
| [CMMI V3.0](https://www.isaca.org/resources/reference-guide/cmmi-model-quick-reference-guide) (ISACA, Apr 2023) | 1 Initial → 2 Managed → 3 Defined → 4 Quantitatively Managed → 5 Optimizing | The canonical "maturity level" ancestry. Elegant parallel: CMMI L4 (quantitative measurement) ≈ our L5 (evals); CMMI L5 (optimizing) ≈ our L6 (learnings loops). Our L7 extends beyond CMMI's scope |
| [Microsoft, Agentic AI adoption maturity model](https://learn.microsoft.com/en-us/agents/adoption-maturity-model/) | Level 100 (Initial) → agent-first optimized | Grades an *organisation's adoption*, not a skill artifact — a complementary axis |
| Gartner, "Agentic AI Maturity Roadmap" (Aug 2025; paywalled, [reseller summary](https://www.skan.ai/analyst-reports/2025-gartner-agentic-ai-maturity-roadmap)) | 5 levels, task automation → expert autonomous systems | Secondary citation only (paywalled); same organisational axis as Microsoft's |

---

## 4. Measurement methodology — what L5 borrows from

Model benchmarks do **not** measure skill maturity (they grade models), but
their *methodology* is exactly what skill evals borrow. Cite these for the
technique, not the leaderboard.

| Source | Technique we borrow |
| --- | --- |
| [SWE-bench](https://arxiv.org/abs/2310.06770) (Jimenez et al., ICLR 2024) + SWE-bench Verified | Task-based, end-to-end verifiable agentic evaluation — the template shape for skill evals |
| [τ-bench](https://arxiv.org/abs/2406.12045) (Yao et al., Sierra) + [τ²-bench](https://github.com/sierra-research/tau2-bench) | Tool-agent-user interaction evals; the **pass^k** reliability metric (run the same case k times — consistency is part of quality) |
| [Terminal-Bench](https://www.tbench.ai/) (Stanford + Laude Institute) | Containerized task + programmatic verifier suite per case |
| [Berkeley Function-Calling Leaderboard](https://gorilla.cs.berkeley.edu/leaderboard.html) (UC Berkeley Gorilla) | Tool-call correctness grading |
| [LiveBench](https://arxiv.org/abs/2406.19314) (Abacus.AI + NYU et al.) | Contamination-free rolling refresh — keep eval cases fresh so skills don't overfit to them |
| [MathArena](https://matharena.ai) (ETH Zurich SRI Lab + INSAIT) | Evaluate on genuinely unseen problems (fresh competitions) with objective ground truth |
| LMArena / Chatbot Arena (ex-LMSYS) | Pairwise-preference + Elo/Bradley-Terry for comparing two skill *variants* when no objective ground truth exists. **Caveats:** now commercial; known critiques (vote gaming, style bias, "Leaderboard Illusion") |
| Zheng et al. 2023, ["Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena"](https://arxiv.org/abs/2306.05685) (NeurIPS 2023) | LLM-as-judge — and its documented biases (position, verbosity, self-preference). Required reading before grading skill output with a model |
| [OpenAI Evals](https://github.com/openai/evals) | Open-source eval framework/registry; useful reference implementation |
| [Prompt Engineering Guide](https://www.promptingguide.ai/) (DAIR.AI) + Anthropic Cookbook | Authoring patterns (L3) and practical eval notebooks incl. LLM-as-judge caveats (L5) |

---

## 5. Assessed and excluded — do not re-add without new evidence

These come up in every "top LLM resources" list (a 20-item list of them was
vetted on 2026-07-26). They were excluded deliberately:

**Category error — human upskilling, not agent-skill maturity.** Hugging Face
LLM Course, DataCamp, DeepLearning.AI courses, Karpathy's videos/nanoGPT,
Cohere LLM University, Sebastian Raschka's books, mlabonne/llm-course,
KDnuggets roadmaps, Awesome-LLM link dumps, Towards Data Science / Ahead of AI
newsletters. All fine for *humans learning about LLMs*; none says anything
about the maturity of a skill artifact. (If we ever write a personal-development
learning path, that's a different document.)

**Category error — model capability, not skill maturity.** Artificial
Analysis Intelligence Index, GPQA Diamond, MMLU-Pro, Humanity's Last Exam.
They rank *models*; a skill's maturity is independent of which model runs it.

**Dead.** Hugging Face Open LLM Leaderboard — officially **retired March
2025** (v1 and v2), archive-only. Useful only as a historical lesson in
benchmark saturation.

**Unverifiable provenance.** benchmarklist.com and llm-benchs.com — anonymous
aggregators with no identifiable operator, no methodology page, no
independent coverage. Opacity is the disqualifier.

**Single-firm content marketing.** benchmarkingagents.com (Digital Signet) —
decent editorial roundup, but it aggregates the primary sources cited in §4;
cite those directly. ai-radar.aoe.com (AOE GmbH) — an honest
ThoughtWorks-style tech radar for AI tooling, but one agency's opinion; at
most a tooling-discovery pointer.

**Attribution traps** (errors found in circulating lists — don't reproduce
them): LiveBench is **Abacus.AI + NYU et al., not ETH Zurich** (MathArena is
the ETH one — they are unrelated projects); the Agent Skills standard is
*published by Anthropic and aligned with* the Agentic AI Foundation, which
does not (yet) formally own it.

---

## 6. User AI-fluency frameworks — the *other* ladder

Skill maturity (L1–L7) grades the **artifact**. A separate, adjacent question
is how proficient the **human using the AI** is. These frameworks grade
users/practitioners, and matter for product decisions (progressive UI,
guided modes, tutorials) in AI products like hermiq. Vetted 2026-07-26.

**The five citable ones, ranked:**

| Source | Shape | Why cite it |
| --- | --- | --- |
| [Anthropic AI Fluency: Framework & Foundations](https://anthropic.skilljar.com/ai-fluency-framework-foundations) — Anthropic Academy course co-developed with Rick Dakan (Ringling College) & Joseph Feller (University College Cork); CC BY-NC-SA; also on [Coursera](https://www.coursera.org/learn/ai-fluency-framework-foundations) and [aifluencyframework.org](https://aifluencyframework.org/) | **The 4Ds: Delegation, Description, Discernment, Diligence** — competency *dimensions*, not levels | The anchor. For a Claude-based product, Anthropic's own academically co-authored framework is the coherent choice; use the 4Ds as the dimensions each level is measured on |
| [EU AI Act Article 4 — AI literacy](https://www.traverssmith.com/knowledge/knowledge-container/the-eu-ai-acts-ai-literacy-requirement-key-considerations/) | Legal obligation, applies since **2 Feb 2025**; national enforcement + penalties from **3 Aug 2026**. Providers *and deployers* must ensure staff AI literacy **calibrated to role, knowledge, and context**; documentation expected (EU AI Office Living Repository) | **The compliance driver, not a framework.** Proficiency-aware features (guided modes, tracked tutorial completion, role-calibrated UI) map directly onto a deployer's Article 4 documentation duty — acutely relevant to Dutch government clients |
| [UNESCO AI competency frameworks](https://www.unesco.org/en/articles/what-you-need-know-about-unescos-new-ai-competency-frameworks-students-and-teachers) (Sept 2024) | Teachers: 15 competencies × 5 dimensions × 3 progression levels (acquire/deepen/create); students: 12 competencies × 4 dimensions × 3 levels (understand/apply/create) | UN-level authority for the *shape*: competencies × 3 progression levels is exactly the pattern for progressive UI tiers |
| [OECD/EC AILit Framework](https://ailiteracyframework.org/) (final June 2026, with Code.org; feeds PISA 2029) | 4 domains: Engage with AI, Create with AI, Manage AI, Shape AI | EU-institutional reinforcement; the domains map well onto consumer → builder → administrator → governance personas. Caveat: scoped to primary/secondary education |
| Microsoft — [Agentic AI adoption maturity model](https://learn.microsoft.com/en-us/microsoft-copilot-studio/guidance/maturity-model-overview) (Levels 100–500, organisational) + [Work Trend Index](https://www.microsoft.com/en-us/worklab/work-trend-index/agents-human-agency-and-the-opportunity-for-every-organization) user segmentation (skeptics → novices → explorers → power users) | Org maturity ladder + the only large-N empirical *user* segmentation | Concrete enterprise example; vendor-research caveat applies |

**Honorable mention:** [Alex Ewerlöf, "AI Fluency Leveling"](https://blog.alexewerlof.com/p/ai-fluency-leveling) (Jan 2026) — 7 levels, Casual Consumer → Prompt Coder → Context Developer → AI Engineer → AI System Architect → AI Platformizer → AI Pioneer. The best practitioner-authored consumer→builder ladder; cite as "one practitioner formulation", not authority.

**The common shape** across every credible framework: 3–7 levels; the same
recurring dimensions (prompting/description sophistication, delegation
judgment, discernment/oversight, building/orchestration,
governance/responsibility); and the universal arc
**consume → direct → verify → compose → govern**. A 4–5 level user model
scored against the Anthropic 4Ds, with UNESCO/OECD's
understand → apply → create progression as the leveling logic and Article 4
as the compliance rationale, sits squarely inside all of them.

**Assessed and excluded from this category** (vetted 2026-07-26): Larridin's
AI Proficiency Model (real a16z-backed startup, but SEO funnel content for
their SaaS); "5 Layers of AI Engineering" (aibuilderclub.com — a system
architecture layering, not human proficiency; paid-community marketing);
"Levels of AI Engineering Proficiency" LinkedIn posts (anonymous-grade, no
citations); the "12-level Prompt Engineering Mastery" progression (**could
not be located at all — treat as apocryphal**); aimlinsights.com and Pertama
Partners (content-farm / regional vendor marketing); KDnuggets roadmaps,
StrataScratch, To Data & Beyond, outcomeschool (legitimate *developer
curricula* or monetized roadmaps — wrong axis for user proficiency; the same
goes for mlabonne/llm-course and the *LLM Engineer's Handbook*, both
excellent for engineer upskilling). The InformationWeek "101–401" agentic
learning model is a real op-ed by Dan Mitchell (Digital Wave Technology, Jul
2026) — citable as illustrative pedagogy only, attributed to Mitchell.

---

## 7. Agent-platform maturity & autonomy (mid-2026 wave)

A third axis next to skill maturity (§1–5) and user fluency (§6): how mature
the **platform/organisation running agents** is, and how much **autonomy** an
agent is granted. Vetted 2026-07-27; four sources survive.

| Source | Shape | What we take from it |
| --- | --- | --- |
| [Pydantic, "A maturity model for applied generative AI"](https://pydantic.dev/articles/applied-generative-ai-maturity-model) (Alex Che, 25 Jun 2026) | 5 levels (Experimenting → Adopted → Observed → Governed → Optimized) × 5 dimensions: visibility/observability, evaluation & quality, cost governance, access & identity, audit & incident response | The eval-coverage ratchet (ad-hoc → suites for critical agents → evals as CI gates → continuous online evals) and cost ladder (dashboards → alerts → server-side caps → per-run unit economics). Advice: fix "the gap currently bleeding", don't chase L5 everywhere |
| [Addy Osmani, "Agentic Autonomy Levels"](https://addyosmani.com/blog/agentic-autonomy-levels/) (2 Jul 2026) | 6 levels L0–L5: Assist → Supervised Action → Scoped Task Delegation → Goal-Driven Autonomy → Parallel Delegation → Managed-by-Exception Orchestration | Graduated per-agent autonomy; the **per-run contract** (goal, scope, non-goals, tool permissions, stopping condition, evidence, escalation, budget); risk-calibrated autonomy (risk × reversibility × available verification); KPIs: mean time between interventions, longest unattended run, auto-approval rate, token cost per accepted change |
| [Arize, "How to write effective AI agent skills: 6 data-backed practices"](https://arize.com/blog/) (Laurie Voss, 24 Jul 2026) | Six practices backed by SkillsBench data | Human-curated beats self-generated (+18–25 pts vs −8–12); compact & procedural wins (comprehensive docs +0.7 pt only); route a **minimal skill set** (1–3 skills ≈ +18–19 pts; all-196 loaded = worse and +23% tokens); test per model×harness ("portable as files, not as behavior"); target gaps the base model can't fill; **every skill change is a paired experiment** against a frozen baseline. "The eval is the skill" |
| CMMI AI Maturity ([CMMI AIM](https://www.isaca.org/), ISACA, launched Jun 2026) | AI content across all 31 CMMI Practice Areas, 8 domains (Data, Development, People, Safety, Security, Services, Suppliers, Virtual collaboration) | Institutional weight for AI-capability maturity; People domain = workforce-readiness as a first-class axis. **Caveat:** model body is behind CMMI licensing — cite only the public structure, under the correct name "CMMI AIM" |

**Assessed and excluded** (2026-07-27): the widely-shared "Hakkoda AI
maturity ladder (LLM velocity → build skills → chain skills → agents →
agents-talk-to-agents)" **could not be located on hakkoda.io as cited** —
their real publications say different things; treat the ladder as
misattributed and back agent-to-agent rungs with Osmani L4–L5 instead.
AgentPatterns.ai's 7-phase adoption model is thoughtful but authorless;
HiBob's "AI Skills Framework" is a press release; The Neuron's 5-level stack
(Projects → Prompting → Skills → Automations → Agents) is consumer
up-skilling content — citable only as a footnote that even consumer guidance
converges on skills → automations → agents; AgenticCareers' career ladder is
job-board content marketing.

**Convergent spine across the four citable sources:** autonomy is granted
per-run against verification capability (Osmani); quality is enforced by
evals-as-gates (Pydantic + Arize); cost, access, and audit are server-side
controls, not dashboards (Pydantic + CMMI).

---

## How the levels map to their strongest sources

| Level | Strongest external grounding |
| --- | --- |
| L1 Anatomy | Agent Skills open standard; Anthropic best practices |
| L2 Triggering | Anthropic best practices (descriptions, progressive disclosure) |
| L3 Patterns | Anthropic best practices; Prompt Engineering Guide; Anthropic Cookbook |
| L4 Personalization | (inherently internal — no external source can supply your business context; e-CF's "competence in context" framing is the analogue) |
| L5 Measurement | Anthropic skill-creator blog; SWE-bench / τ-bench / Terminal-Bench / BFCL methodology; Zheng 2023 for LLM-as-judge caveats |
| L6 Self-Improvement | MindStudio learnings loop; community implementations; CMMI L5 "Optimizing" as ancestry |
| L7 AI Workforce | Zhang & Murag talk; Claude Code Agent Teams / Agent SDK docs; Microsoft agentic maturity model as the organisational mirror |
