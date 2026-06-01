---
status: filled
options:
  - id: O1
    name: "Measurement audit of AI grocery recommendations"
    project_type: measurement
    identification: "Repeated black-box prompts across household personas; no causal treatment, but systematic measurement of affordability, nutrition, feasibility, and stability using D001, D002, D005, and D007."
    viability_condition: "D005 reports at least two nutrition measurement sources and at least two affordability measurement sources."
    viability_test:
      metric: nutrition_measurement_sources
      op: ">="
      threshold: 2
    max_claim: measurement
    threats_addressed: []
    priority: 1
    is_fallback_floor: false
    claim_boundary: "Can claim measured differences in generated recommendations under the audit protocol; cannot claim real consumer effects or platform-wide behavior outside sampled prompts/models."
  - id: O2
    name: "Equity comparison across SNAP-relevant household personas"
    project_type: descriptive
    identification: "Compare scored recommendation baskets across pre-registered synthetic household profiles varying budget, household size, food access, dietary constraints, and SNAP-relevant context."
    viability_condition: "D005 reports at least four high-priority sources and all scouted sources have concrete next probes."
    viability_test:
      metric: high_priority_sources
      op: ">="
      threshold: 4
    max_claim: descriptive
    threats_addressed: []
    priority: 2
    is_fallback_floor: false
    claim_boundary: "Can describe profile-contingent recommendation quality in the audit sample; cannot identify discrimination in a legal sense or infer actual household health outcomes."
  - id: O3
    name: "Affordability stress test against SNAP/TFP benchmark"
    project_type: policy-translation
    identification: "Score generated baskets against Thrifty Food Plan/SNAP-relevant affordability thresholds and available price locators, treating price capture as a feasibility bottleneck."
    viability_condition: "D005 reports at least two affordability measurement sources."
    viability_test:
      metric: affordability_measurement_sources
      op: ">="
      threshold: 2
    max_claim: measurement
    threats_addressed: []
    priority: 3
    is_fallback_floor: false
    claim_boundary: "Can translate recommendation costs into policy-relevant budget pressure; cannot claim precise local shopping costs until retailer price collection is validated."
  - id: O_floor
    name: "Scoping-only descriptive evidence map"
    project_type: descriptive
    identification: "Always-viable fallback summarizing candidate data sources, closest literature, and required measurement protocol without collecting AI recommendation outputs."
    viability_condition: "Always viable from completed G1 discovery artifacts."
    viability_test:
      metric: candidate_sources_total
      op: always
      threshold: 0
    max_claim: descriptive
    threats_addressed: []
    priority: 9
    is_fallback_floor: true
    claim_boundary: "Can only claim that the project is or is not ready for a full audit; cannot make empirical claims about AI recommendation quality."
---

# Design Options: Ranked Candidate Research Designs

## Selection Rule

Select the lowest-priority option whose viability test passes using `discovery/data_diagnostics.yml`. If O1 passes, proceed with a measurement audit as the main design. If O1 fails but O2 or O3 passes, downgrade the study to a narrower descriptive or policy-translation audit. If only `O_floor` passes, stop at a scoping evidence map and do not claim empirical recommendation quality.

## Option O1

O1 is the preferred design because it directly matches the project idea: generate AI grocery recommendations under controlled household constraints, parse them into purchasable food items, and score the outputs for nutrition, affordability, feasibility, and repeated-run stability. Its main strength is that it treats the AI system as a black box and makes the audit protocol reproducible. Its main limitation is external validity: the results will describe sampled prompts, models, and time windows rather than all AI grocery advice.

## Option O2

O2 focuses on equity across SNAP-relevant household personas. It uses the same output-scoring logic as O1 but emphasizes between-profile comparisons such as whether low-budget or low-access households receive less actionable recommendations. This option is descriptive rather than causal because persona differences are prompt-defined and do not identify real-world discrimination mechanisms.

## Option O3

O3 narrows the study to affordability and policy translation. It asks whether generated baskets fit plausible SNAP/Thrifty Food Plan constraints and whether the recommendation system acknowledges binding budget limits. This option is useful if nutrition measurement remains feasible but full output parsing or retailer price capture is only partially validated.

## Option O_floor

The fallback floor is a scoping evidence map. It preserves value if AI output collection or price matching is not yet feasible by documenting the literature gap, data sources, and measurement protocol required for a later full audit. It intentionally earns only a descriptive readiness claim.
