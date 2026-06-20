# Extraction Card — L2 AIGS

- paper_id: L2
- citation: Liu, Zijun; Liu, Kaiming; Zhu, Yiqi; Lei, Xuanyu; Yang, Zonghan; Zhang, Zhenhe; Li, Peng; Liu, Yang. "AIGS: Generating Science from AI-Powered Automated Falsification." Tsinghua University & Institute for AI Industry Research (AIR).
- locator: arXiv:2411.11910v2 [cs.LG], 24 Nov 2024
- opened: full PDF text extracted (pdftotext) and read, 2026-06-20
- function: method-identification / theory-mechanism (falsification-as-engine)

## Direct evidence notes (section/line-anchored)

- **Core thesis (abstract):** "By revisiting the definition of scientific research
  (Popper, 1935), we argue that **falsification is the essence of both human research
  process and the design of an AIGS system.**" Through the falsification lens, prior
  AI-science systems "either lack the part in their design, or rely heavily on
  existing verification engines that narrow the use in specialized domains."
- **System (abstract, §method):** **BABY-AIGS** = "a baby-step demonstration of a
  full-process AIGS system," multi-agent with roles for the research process
  (ReviewAgent, **FalsificationAgent**, etc.). Operates in two phases; falsification
  is "a key feature absent in prior systems (Lu et al., 2024)."
- **FalsificationAgent mechanism (§, ~line 723):** "responsible for doing the
  **ablation studies** and deriving scientific discoveries as the final outcome...
  takes the multi-turn log of all [prior work] as history context."
- **Honest self-assessment (abstract):** experiments on three tasks "preliminarily
  show that BABY-AIGS could produce meaningful scientific discoveries, **though not
  on par with experienced human researchers**." Limitations + ethics in §4.

## What this card CAN support
- That a credible, peer-reviewed line argues **falsification (Popper) should be the
  organizing principle** of automated research — independent external support for
  AEROS making negative results / placebo / robustness first-class rather than a
  checklist.
- That an explicit FalsificationAgent (ablation-driven) is a concrete design pattern
  AEROS could adapt for its robustness lane.

## What this card CANNOT support
- It is explicitly a "baby-step," below human-researcher performance — cannot be
  cited as proof that automated falsification *works* at research grade.
- It addresses ML-style discovery tasks, not empirical social-science identification;
  transfer to AEROS's econ/applied-micro setting is unverified.

## Relevance to AEROS
Validates AEROS's instinct but also shows the frontier is early. Borrowable: reframe
AEROS's robustness/placebo lane from a *checklist* into an active, ablation-driven
**falsification engine** (a FalsificationAgent analog) that attacks the headline
claim rather than waiting to be asked.
