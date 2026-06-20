# Extraction Card — L1 HLER

- paper_id: L1
- citation: Zhu, Chen & Wang, Xiaolu. "HLER: Human-in-the-Loop Economic Research via Multi-Agent Pipelines for Empirical Discovery." China Agricultural University.
- locator: arXiv:2603.07444v1 [cs.AI], 8 Mar 2026. Repo: github.com/maxwell2732/hler-working-papers
- opened: full PDF text extracted (pdftotext) and read, 2026-06-20
- extraction_depth: full_text_extraction
- function: gap-verification + method-identification (closest existing analog to AEROS)

## Direct evidence notes (section/line-anchored to extracted text)

- **Pipeline (abstract/§1):** specialized agents for "data auditing, data profiling,
  hypothesis generation, econometric analysis, manuscript drafting, and automated
  review."
- **Headline mechanism — dataset-aware hypothesis generation (§1, contributions):**
  candidate questions "constrained by dataset structure, variable availability,
  missingness, and distributional diagnostics... This prevents infeasible or
  hallucinated hypotheses." Contribution 1: "reducing infeasible hypotheses from
  **59% to 13%** compared with unconstrained LLM ideation."
- **Two-loop architecture (§1):** (i) *question quality loop* = generation →
  feasibility screening → **human selection**; (ii) *research revision loop* =
  automated review → re-analysis → revision.
- **Human decision gates (abstract):** "embedded at key stages, including
  **question selection and publication approval**." (NOTE: an earlier machine
  summary invented "approval of novel theoretical claims"; the real, verified gates
  are question-selection and publication-approval.)
- **Quantitative (abstract):** feasible questions **87%** (dataset-aware) vs **41%**
  (unconstrained); **14 pipeline runs**, 3 datasets incl. longitudinal survey;
  end-to-end manuscripts at **$0.8–$1.5/run**; CHNS (China Health & Nutrition
  Survey) case study.
- **Motivation/limits cited (§1):** hallucination ("fluent but unsupported claims");
  replication audits show reproducing published economics findings "often fails or
  requires substantial author assistance"; analytic-choice sensitivity ("different
  teams can arrive at meaningfully different estimates").

## What this card CAN support
- The claim that an autonomous-research system **closely analogous to AEROS exists**
  for empirical economics: stage decomposition + human gates + data-feasibility
  constraint, with measured feasibility gains.
- That **constraining hypotheses by data feasibility** (AEROS's data-first instinct)
  has *measured* value (infeasible 59%→13%).

## What this card CANNOT support
- It does NOT report a claim-ceiling calculus, evidence-type lattice, no-laundering
  rule, provenance boundary, or preregistration — so it does not refute AEROS's
  distinct integrity-layer niche.
- HLER's quantitative gains are about feasibility/reviewer-score, not research
  *correctness*; cannot be cited as evidence that such pipelines produce *valid*
  findings.

## Relevance to AEROS
Strongest "prior art" for AEROS's overall thesis. Borrowable: HLER's dataset-aware
generation as a *measured* operationalization of AEROS's data-first gate, and its
explicit human gates (question selection + publication approval) map onto AEROS
gates. Gap AEROS fills vs HLER: the admissibility/claim-ceiling layer.
