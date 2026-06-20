# Related Work: AEROS vs Autonomous-Research Systems

Status: provisional positioning pass (2026-06-20). Produced by running the AEROS
literature workflow — search → registry → extraction → synthesis — on the
autonomous-/LLM-research literature, to locate AEROS's niche.

**Honesty note (AEROS rule: abstract-only ≠ full-text evidence).** This pass did
NOT reach gold-standard full-text extraction. Two papers were fetched and
machine-summarized (partial); three remain at search-snippet/abstract level
(PDF resisted extraction or exceeded fetch limits). Treat the synthesis as a
*positioning hypothesis*, not verified gap evidence. Strong claims need real
full-text extraction cards.

## 1. Search

Three web searches (2026-06-20): autonomous AI-scientist systems; limitations/
risks of automated science; multi-agent role-separation + human-in-the-loop.

## 2. Registry

| id | paper | locator | function | screening | extraction depth |
|----|-------|---------|----------|-----------|------------------|
| L1 | HLER: Human-in-the-Loop Economic Research | arXiv 2603.07444 | gap-verification / method (closest analog) | include-candidate | partial (fetched, summarized) |
| L2 | AIGS: Generating Science from AI-Powered Automated Falsification | arXiv 2411.11910 | method / mechanism | include-candidate | partial (fetched, summarized) |
| L3 | Agent Laboratory: LLM Agents as Research Assistants | arXiv 2501.04227 | method (role-based system) | maybe | abstract/snippet (fetch failed) |
| L4 | Creativity-Centered Survey: LLMs for Scientific Idea Generation | arXiv 2511.07448 | theory/mechanism (the validation-wall) | include-candidate | abstract/snippet (fetch too large) |
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
2. **The bottleneck is validation, not generation** (L4). Scaling generation
   without scaling trustworthy evaluation produces *plausible pseudo-science* that
   automated reviewers miss (L4, L5).
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

Five papers, snapshot, extraction below AEROS's full-text bar (only 2 fetched, both
machine-summarized). Not a systematic review. Before any of this supports a formal
"gap" claim about AEROS, the L1/L2/L4 papers need real full-text extraction cards.
