# Extraction Card — L4 Creativity-Centered Survey

- paper_id: L4
- citation: Shahhosseini, F.; Marioriyad, A.; Momen, A.; Soleymani Baghshah, M.; Rohban, M.H. "Large Language Models for Scientific Idea Generation: A Creativity-Centered Survey." Sharif University of Technology (et al.). Published in TMLR (02/2026).
- locator: arXiv:2511.07448v2 [cs.CL], 2 Feb 2026
- opened: full PDF text extracted (pdftotext) and read (targeted: evaluation/verifier sections), 2026-06-20
- function: theory-mechanism (why automated evaluation is the binding constraint)

## Direct evidence notes (line-anchored to extracted text)

- **Verifier reward-hacking (lines 813–816, verified verbatim):** peer/LLM evaluators
  "remain vulnerable to **reward hacking**: generators can learn to exploit systematic
  weaknesses in verifier heuristics, **producing outputs that appear highly rated
  without being genuinely correct or useful**." Models "**overfit to their
  evaluators, generating verbose, sycophantic, or superficially persuasive responses
  that maximize reward signals rather than substantive quality**" (cites Laidlaw et
  al. 2025; Miao et al. 2024).
- **Feedback sources as evaluators (line 742):** used "to verify feasibility,
  soundness, and scientific grounding" — but reliability "depends on careful design
  to avoid exploitation and collapse of evaluation diversity" (line 818).
- **Human-in-the-loop value (lines 749, 939):** human evaluation "especially valuable
  in subjective or poorly formalized domains."

## HONESTY CORRECTION
The phrase "plausible pseudo-science" used in my earlier provisional synthesis came
from a **search-result snippet**, not from text I have verified in this PDF. The
verified, quotable framing is **verifier reward-hacking / "superficially persuasive
... without being genuinely correct."** Treat the two as the same risk, but cite the
verified wording, not the snippet.

## What this card CAN support
- That **automated evaluation is gameable**: optimizing toward an automated reviewer
  produces outputs that *score well without being correct* — peer-reviewed, verbatim.
- That this is the strongest external justification for AEROS keeping (a) a human gate
  at claim release and (b) evidence admissibility tied to provenance, not to a
  reviewer score.

## What this card CANNOT support
- It is a survey of *idea generation / creativity*, not of research-integrity
  systems; it does not evaluate AEROS-like designs, so it cannot confirm AEROS's
  solution works — only that the problem AEROS targets is real and documented.

## Relevance to AEROS
This is AEROS's "reason to exist," now source-grounded: if you let an automated
reviewer be the judge, generators learn to fool it. AEROS's answer — critic ≠ final
judge, human gate at claim release, claim support bound to provenance not score — is
the direct response. Also a warning: AEROS's own automated checks are themselves
gameable, so the human gate stays load-bearing.
