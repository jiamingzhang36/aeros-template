# Related Work: AEROS vs Autonomous-Research Systems

Status: positioning pass (2026-06-20; full-text extraction added for L1/L2/L4).
Produced by running the AEROS literature workflow — search → registry → extraction
→ synthesis — on the autonomous-/LLM-research literature, to locate AEROS's niche.

**Extraction status (AEROS rule: abstract-only ≠ full-text evidence).** L1 (HLER),
L2 (AIGS), and L4 (creativity survey) now have **real full-text extraction cards**
(`docs/related_work_cards/`) — their PDFs were extracted with `pdftotext` and read
directly. L3 (Agent Laboratory) and L5 (LLM-REVal) remain at snippet level. The
synthesis below now rests on three full-text cards; statements that depend on L3/L5
are still provisional.

**What full-text extraction corrected** (the point of the rule): (a) HLER's real
human gates are *question selection + publication approval* — an earlier machine
summary had invented "approval of novel theoretical claims"; (b) the creativity
survey's verified risk framing is *verifier reward-hacking / "superficially
persuasive without being genuinely correct"* — "plausible pseudo-science" was a
search-snippet paraphrase, not verified text.

## 1. Search

Three web searches (2026-06-20): autonomous AI-scientist systems; limitations/
risks of automated science; multi-agent role-separation + human-in-the-loop.

## 2. Registry

| id | paper | locator | function | screening | extraction depth |
|----|-------|---------|----------|-----------|------------------|
| L1 | HLER: Human-in-the-Loop Economic Research | arXiv 2603.07444 | gap-verification / method (closest analog) | **include** | **full_text (card)** |
| L2 | AIGS: Generating Science from AI-Powered Automated Falsification | arXiv 2411.11910 | method / mechanism | **include** | **full_text (card)** |
| L3 | Agent Laboratory: LLM Agents as Research Assistants | arXiv 2501.04227 | method (role-based system) | maybe | abstract/snippet |
| L4 | Creativity-Centered Survey: LLMs for Scientific Idea Generation | arXiv 2511.07448 | theory/mechanism (the validation-wall) | **include** | **full_text (card)** |
| L5 | LLM-REVal: Can We Trust LLM Reviewers Yet? | arXiv 2510.12367 | method (reviewer trust) | maybe | abstract/snippet |
| B1 | The AI Scientist / AI-Researcher / FARS (cluster) | various | background / idea-inspiring | defer | snippet only |

## 3. Extraction notes (graded)

**L1 HLER [partial].** Multi-agent pipeline automating empirical *economics*:
problem formulation → literature synthesis → hypothesis generation → experimental
design → result interpretation; humans stay at decision gates (validate research
directions, verify data preprocessing, review statistical findings, approve novel
theoretical claims); keeps audit trails of agent reasoning; explicitly does NOT
replace human judgment in theory/policy, novel dataset creation, or complex causal
inference. → The closest existing analog to AEROS, same "automate the stages,
keep humans at the gates" thesis. (Exact gate list unverified — summarized.)

**L2 AIGS [partial].** Treats *falsification* as the primary validation mechanism
(vs confirmation-seeking); roles = theory-generation / experiment-design /
analysis / critique agents in iterative cycles; safeguards = reproducibility
across conditions, automated contradiction detection, constraint-violation
tracking; does NOT guarantee ground-truth or replace human judgment. → Validates
AEROS's instinct to make negative results / placebo / robustness first-class.

**L3 Agent Laboratory [abstract].** Planner/Critic/Experimenter/Coder cyclical
workflow (from search snippet); full mechanisms unverified (PDF not extracted).

**L4 Creativity survey [abstract, but with direct quotes from search]:**
"reliable evaluation is fundamentally harder than generation"; risk of
**"plausible pseudo-science"** — ideas that "appear coherent and innovative yet
rest on incorrect assumptions or unsound reasoning that automated evaluators
struggle to detect"; warns of bias toward dominant paradigms. → The single
strongest external justification for AEROS's whole premise.

**L5 LLM-REVal [abstract].** Questions whether LLM reviewers can be trusted →
supports AEROS keeping critic ≠ final judge, human gate at claim release.

## 4. Synthesis (provisional)

1. **The field already imitates the research workflow.** AI-scientist systems
   decompose science into staged, role-specialized agent pipelines — structurally
   the same move as AEROS's lanes/gates.
2. **The bottleneck is validation, not generation** (L4, full-text verified).
   Automated evaluators are gameable: generators "exploit systematic weaknesses in
   verifier heuristics, producing outputs that appear highly rated without being
   genuinely correct or useful" and become "superficially persuasive ... rather than
   substantive quality" (L4, lines 813–816). I.e. optimizing toward an automated
   reviewer manufactures convincing-but-wrong results — and AIGS (L2) independently
   argues falsification must be the counter-discipline.
3. **Most systems optimize end-to-end automation and reviewer scores; few make an
   integrity/admissibility layer a first-class citizen.** AIGS (falsification, L2)
   and HLER (human gates, L1) are the closest, but neither reports a claim-ceiling
   calculus, evidence-type lattice, no-laundering rule, or provenance boundary.

## 5. Positioning table

| Dimension | Typical "AI Scientist" | HLER (L1) | AIGS (L2) | **AEROS** |
|---|---|---|---|---|
| Primary target | end-to-end automation, reviewer score | assisted econ discovery | automated falsification | **what is *allowed to be claimed*** |
| Role separation | yes (planner/critic/...) | yes | yes | yes (worker/critic/human-gate + lanes) |
| Human-in-the-loop | minimal/optional | **yes, at gates** | partial | **yes, hard gate at claim release** |
| Falsification / negative results | rare | — | **core** | core (placebo, robustness, negative-result ledger) |
| Provenance / event log / hashing | rare | audit trails | — | **content-addressed, append-only events (aspirational)** |
| Evidence admissibility / no-laundering | absent | — | — | **explicit lattice + boundary** |
| Claim-ceiling / anti-pseudo-science | absent | — | implicit | **explicit compiler** |

## 6. What AEROS can learn / its gaps (honest)

- **AEROS has no benchmark of its own value.** HLER reports quantitative gains
  (e.g., revision loops raising reviewer scores); AEROS has *no* measured evidence
  it improves research outcomes — only internal consistency. This is its biggest
  unproven claim.
- **Borrow AIGS's falsification-as-engine framing** to strengthen AEROS's robustness/
  placebo lane from checklist to active hypothesis-attacking.
- **Borrow HLER's explicit stage decomposition** to sharpen lane/gate definitions
  for econ projects specifically.
- **The "plausible pseudo-science" risk (L4) is AEROS's reason to exist** — but it
  also warns AEROS's own automated checks could miss unsound-but-coherent results;
  human gates remain load-bearing.

## 7. Limitations of this review

Five papers, snapshot. **L1/L2/L4 now have full-text extraction cards**
(`docs/related_work_cards/`); L3/L5 remain snippet-level, so any statement leaning on
them is provisional. Still not a systematic review — three full-text papers is a
positioning sketch, not exhaustive coverage; a formal gap claim would need a
broader, pre-specified search + screening. AIGS (L2) is explicitly a "baby-step"
below human-researcher performance and HLER's (L1) metrics measure feasibility/
reviewer-score, not research correctness — so neither supports "these systems
produce *valid* findings," only that the workflow and its failure modes are real.
