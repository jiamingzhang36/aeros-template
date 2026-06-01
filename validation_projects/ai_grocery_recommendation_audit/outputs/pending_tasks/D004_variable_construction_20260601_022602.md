# Manual AEROS Task Prompt

AEROS_AGENT_PROVIDER=manual wrote this prompt instead of calling an agent.

Fill the allowed output files, then run `aeros check <task-contract>`.

```text
You are an AEROS worker agent executing task D004_variable_construction (stage: discovery).

## Goal
G2 Measurement. For every key variable the candidate designs need, specify how it is constructed from a real data source and whether it can actually be built. This is the bridge between the data (G1) and the designs (G3): a design that needs a variable that cannot be constructed is not feasible.
Read the design options (the variables each design's treatment/outcome/ identification needs) and the data inventory (the available sources). Write discovery/variable_construction.md with this front matter:

  ---
  status: filled
  variables:
    - name: exposure_or_treatment
      role: treatment        # treatment|outcome|control|instrument|moderator|unit-key|running-variable
      definition: "project-specific variable definition"
      source_data_id: D001   # MUST exist in data_inventory.csv
      construction: "project-specific construction rule"
      validity_concern: "main measurement or linkage concern"
      constructible: uncertain # yes | no | uncertain (be honest)
    - name: outcome_variable
      role: outcome
      ...
  ---

and a "## <variable name>" prose section per variable.
Requirements: - Define at least one treatment and one outcome variable. - Every variable maps to a real source_data_id from data_inventory.csv. - Mark constructible honestly (no/uncertain when the data does not clearly
  support it); do not mark everything 'yes'. The constructible flags are what
  G1-G3 feasibility reads.

## You may write ONLY these files
- discovery/variable_construction.md

## Forbidden
- Do not write anywhere under data/raw/ (enforced by a hook).
- Do not invent data sources; every source_data_id must already be in data_inventory.csv.
- Do not mark a variable constructible=yes unless the named source plausibly supports it; prefer 'uncertain' when unsure.

## Inputs (read-only context)
--- discovery/design_options.md ---
---
status: draft
options: []
---

# Design Options: Ranked Candidate Research Designs

Populate during discovery. Keep at least one fallback floor design before adjudication.

## Selection Rule

TBD


--- discovery/data_inventory.csv ---
data_id,dataset_name,owner_or_source,access_status,unit,intake_ref,intake_priority,geography,period,key_variables,link_or_path,restrictions,access_evidence,engineering_status,skills_considered,skills_used,skill_probe_status,next_probe,feasibility_status,notes
D001,FoodData Central API,USDA Agricultural Research Service,public,food item,idea_memo,high,United States,current and historical releases,"food description; nutrients; branded food identifiers; serving sizes; ingredients; FDC ID",https://fdc.nal.usda.gov/api-guide,"API key may be required for higher-volume use; product matching from AI text to FDC records must be validated","Official API guide located; source documents Foundation Foods, FNDDS, SR Legacy, and Global Branded Foods access",located,"data-inventory; data-quality-checker",data-inventory,not_started,"Run a small API search for 20 common grocery items and measure match rate plus missing nutrient fields",TBD,"Primary source for nutritional reasonableness scoring of generated grocery recommendations."
D002,USDA Thrifty Food Plan 2021,USDA Food and Nutrition Service,public,market basket / household budget,idea_memo,high,United States,2021 onward,"reference grocery budget; SNAP allotment benchmark; age-sex household cost adjustments; food categories",https://www.fns.usda.gov/CNPP/thrifty-food-plan-2021,"Report and cost tables are public but may need manual extraction or separate monthly cost files","Official FNS page located; page states TFP 2021 market basket costs serve as basis for SNAP benefit allotments",located,"data-inventory; policy-timeline",data-inventory,not_started,"Extract relevant household budget benchmarks and map them to audit personas for affordability thresholds",TBD,"Useful benchmark for SNAP-relevant affordability rather than treating arbitrary dollar cutoffs as policy-grounded."
D003,Food Access Research Atlas,USDA Economic Research Service,public,census tract,idea_memo,medium,United States,latest ERS release,"low-income tract indicators; low-access indicators; vehicle access; distance to stores; population counts",https://www.ers.usda.gov/data-products/food-access-research-atlas/download-the-data/,"Geographic linkage required; may be too coarse if the audit does not condition prompts on location","Official ERS download page located for Food Access Research Atlas data",located,"data-inventory; policy-timeline",data-inventory,not_started,"Download metadata only or inspect schema later; decide whether personas need tract-level food-access constraints",TBD,"Could support equity/persona construction but may be optional if audit uses synthetic household constraints without tract assignment."
D004,Food Environment Atlas,USDA Economic Research Service,public,county / state / local area,idea_memo,medium,United States,latest ERS release,"SNAP participation context; food insecurity; food stores; socioeconomic environment; food access variables",https://primary.ers.usda.gov/data-products/food-environment-atlas/documentation,"Atlas variables are aggregate and may not match product-level recommendations","Official ERS documentation located; documentation describes USDA/FNS/AMS/NASS source integration",located,"data-inventory",data-inventory,not_started,"Inspect variable guide and select a minimal set of context variables for persona realism",TBD,"Background/context source for equity dimensions, not a direct scoring source for AI output quality."
D005,Open Food Facts API,Open Food Facts,public,branded food product,idea_memo,medium,global with US coverage,current community database,"barcode; product name; ingredients; allergens; nutrition facts; labels; categories",https://openfoodfacts.github.io/openfoodfacts-server/api/,"Community-contributed coverage and quality vary; price coverage is separate and incomplete","API documentation located; source describes product endpoint and product-label nutrition data",located,"data-inventory; data-quality-checker",data-inventory,not_started,"Query a small sample of AI-recommended branded/generic items and measure coverage against USDA FoodData Central",TBD,"Useful as a product-label crosswalk and robustness source, especially for branded recommendations."
D006,Online grocery retailer product and price pages,Major grocery retailers or delivery platforms,restricted,store-product-day,idea_memo,high,United States / selected markets,current,"product title; package size; listed price; availability; store location; SNAP/EBT acceptance indicator where visible",https://www.walmart.com/cp/food/976759,"Terms of service, bot controls, location dependence, and price personalization may restrict automated collection","Representative public grocery category page located; no access claim beyond visible web locator",located,"data-inventory; webapp-testing",data-inventory,not_started,"Choose one retailer and manually inspect whether small-scale price capture is allowed and reproducible for a fixed ZIP code",TBD,"Potentially essential for real affordability scoring, but high legal/engineering risk; should not be pursued without explicit collection protocol."
D007,Synthetic AI recommendation audit outputs,Project-generated prompt response corpus,unknown,prompt-profile-run,idea_memo,high,United States / synthetic personas,not yet collected,"prompt; model/provider; timestamp; household profile; recommended items; quantities; rationale; repeated-run identifier",outputs/audit_runs/,"Must avoid private user data; model terms and reproducibility constraints apply","No corpus exists yet; this row defines the project-generated outcome data needed by the audit",not_started,"data-inventory; replication-check",data-inventory,not_started,"Design a minimal prompt grid with household profiles, repetitions, and output parser before collecting any model responses",TBD,"Core outcome source for stability and equity analysis; cannot be feasible until prompt protocol is specified."


--- discovery/literature/framing_deck.yml ---
idea: "Audit whether AI-generated grocery recommendations remain stable, affordable, nutritionally reasonable, and equitable under realistic household and SNAP-relevant constraints."
cards:
  - id: F01
    function: gap-verification
    framework: "Empirical evaluation of LLM-generated diet and meal-planning advice"
    rationale: "The closest rival literature is not general recommender-system theory, but empirical studies that prompt large language models to generate diet or meal plans and then evaluate nutritional adequacy, guideline compliance, and practical usability."
    role: motivation
    caveat: "Many existing studies focus on clinical meal planning rather than grocery-basket recommendations under price, store, household, and SNAP constraints, so D001b must verify whether any paper directly audits grocery recommendations rather than adjacent meal plans."
    decision: proposed
    anchors:
      - author: "Fornari"
        year: 2026
        title: "Large Language Models as Clinical Nutrition Decision Tools: Quantitative Bias and Guideline Deviation in Type 2 Diabetes Meal Planning"
        openalex_id: ""
        doi: ""
        verification_status: pending
        kind: empirical
      - author: "BMC Nephrology authors"
        year: 2026
        title: "Assessment of large language model chatbots for hemodialysis meal planning: a descriptive study"
        openalex_id: ""
        doi: ""
        verification_status: pending
        kind: empirical

  - id: F02
    function: method-identification
    framework: "Algorithm audit and black-box testing of online decision systems"
    rationale: "The study needs a repeatable audit design: controlled personas, scripted prompts, repeated model calls, and outcome scoring that treats the AI system as a black box whose outputs can be sampled and compared."
    role: measurement-strategy
    caveat: "Audit results can be sensitive to prompt wording, model version, location, account state, and stochastic generation, so the design must log prompts, timestamps, model identifiers, repetitions, and scoring rules before making claims."
    decision: proposed
    anchors:
      - author: "Sandvig"
        year: 2014
        title: "Auditing Algorithms: Research Methods for Detecting Discrimination on Internet Platforms"
        openalex_id: ""
        doi: ""
        verification_status: pending
        kind: method
      - author: "Raji"
        year: 2020
        title: "Closing the AI Accountability Gap: Defining an End-to-End Framework for Internal Algorithmic Auditing"
        openalex_id: ""
        doi: ""
        verification_status: pending
        kind: method

  - id: F03
    function: theory-mechanism
    framework: "Algorithmic fairness and allocation under constrained choice"
    rationale: "The equity mechanism is that recommendation systems may generate formally similar advice that is practically unequal when households differ in income, transport, store access, time, dietary needs, or eligibility constraints."
    role: mechanism-tested
    caveat: "Fairness concepts from classification may not map cleanly onto grocery recommendation quality, so the project must define fairness as differences in actionable affordability, nutritional adequacy, feasibility, and stability across household profiles."
    decision: proposed
    anchors:
      - author: "Barocas"
        year: 2016
        title: "Big Data's Disparate Impact"
        openalex_id: ""
        doi: ""
        verification_status: pending
        kind: theory
      - author: "Mehrabi"
        year: 2021
        title: "A Survey on Bias and Fairness in Machine Learning"
        openalex_id: ""
        doi: ""
        verification_status: pending
        kind: review

  - id: F04
    function: data-measurement
    framework: "Nutritional adequacy, food-price, and basket-feasibility measurement"
    rationale: "The project needs measurement rules that translate generated recommendations into comparable baskets with calories, macronutrients, food groups, cost, availability, substitutions, and constraint violations."
    role: measurement-strategy
    caveat: "Nutrition and price scoring can create false precision if recipes are underspecified, package sizes differ, local prices vary, or recommendations include vague items such as 'healthy snacks' rather than concrete purchasable products."
    decision: proposed
    anchors:
      - author: "USDA"
        year: 2020
        title: "Dietary Guidelines for Americans, 2020-2025"
        openalex_id: ""
        doi: ""
        verification_status: pending
        kind: data
      - author: "USDA Economic Research Service"
        year: 2021
        title: "Thrifty Food Plan, 2021"
        openalex_id: ""
        doi: ""
        verification_status: pending
        kind: data

  - id: F05
    function: background-institutional
    framework: "Food insecurity, SNAP purchasing constraints, and local food access"
    rationale: "SNAP-relevant grocery advice is embedded in institutional constraints: benefit budgets, eligible foods, retailer availability, transportation, store formats, household composition, and time costs."
    role: motivation
    caveat: "A model can recommend a nutritionally ideal basket that is institutionally infeasible if it ignores SNAP eligibility, local store access, culturally familiar foods, or the timing and lumpiness of benefit disbursement."
    decision: proposed
    anchors:
      - author: "Ver Ploeg"
        year: 2009
        title: "Access to Affordable and Nutritious Food: Measuring and Understanding Food Deserts and Their Consequences"
        openalex_id: ""
        doi: ""
        verification_status: pending
        kind: data
      - author: "Andreyeva"
        year: 2015
        title: "The Supplemental Nutrition Assistance Program and Food Insecurity"
        openalex_id: ""
        doi: ""
        verification_status: pending
        kind: empirical

  - id: F06
    function: method-identification
    framework: "Stability and sensitivity analysis for stochastic recommender outputs"
    rationale: "Because generative AI outputs may vary across repeated calls, the audit should estimate within-profile stability and cross-profile sensitivity rather than treating one response as the system's recommendation."
    role: robustness-comparison
    caveat: "Observed instability may reflect random generation settings, hidden system updates, or prompt ambiguity rather than a stable property of the model, so the audit must distinguish stochastic variance from systematic bias."
    decision: proposed
    anchors:
      - author: "Manski"
        year: 2013
        title: "Public Policy in an Uncertain World: Analysis and Decisions"
        openalex_id: ""
        doi: ""
        verification_status: pending
        kind: method
      - author: "Mitchell"
        year: 2019
        title: "Model Cards for Model Reporting"
        openalex_id: ""
        doi: ""
        verification_status: pending
        kind: method


--- project_manifest.yml ---
project:
  name: AI Grocery Recommendation Audit
  version: '1.0'
  template: aeros-template
  status: draft
  private_by_default: true
research:
  field_or_domain: food policy; algorithm audit; AI recommendation systems
  topic: AI-generated grocery recommendation audit under realistic food policy constraints
  one_sentence_question: We audit whether AI-generated grocery recommendations are
    stable, affordable, nutritionally reasonable, and equitable across realistic household
    constraints, with special attention to low-income and SNAP-relevant food choice
    environments.
  current_stage: discovery
  human_owner: ''
  collaborators: []
gate_lifecycle:
  current_gate: G0 Project Intake
  gates:
  - G0 Project Intake
  - G1 Data Readiness
  - G2 Measurement / Variable Construction
  - G3 Research Design
  - G4 Main Estimation
  - G5 Robustness
  - G6 Result Validation
  - G7 Claim Audit
  - G8 Referee Simulation
  - G9 Replication Package
automation:
  agent_provider: manual
  pipeline:
    cwd: .
    command:
    - python3
    - code/99_make_all.py
    - --mode
    - smoke
    key_outputs: []
    notes: Template placeholder. Replace with the instantiated project pipeline command.
gate_exit_criteria:
  G1:
    requires:
    - type: check_passes
      check: check_data_diagnostics.py
  G2:
    requires:
    - type: check_passes
      check: check_variable_construction.py
  G3:
    requires:
    - type: check_passes
      check: check_design_options.py
    - type: check_passes
      check: check_design_selection.py
    - type: markdown_status_equals
      path: docs/method_card.md
      value: filled
  G4:
    requires:
    - type: claim_main_results_registered
      path: evidence/claim_registry.md
    - type: claim_main_results_have_provenance
      path: evidence/claim_registry.md
  G5:
    requires:
    - type: file_exists
      path: docs/robustness_checklist.md
    - type: status_not_empty
      path: docs/robustness_checklist.md
  G6:
    requires:
    - type: claim_main_results_have_provenance
      path: evidence/claim_registry.md
    - type: result_index_all_have_provenance
      path: evidence/result_index.csv
  G7:
    requires:
    - type: claim_no_draft
      path: evidence/claim_registry.md
    - type: claim_main_has_type
      path: evidence/claim_registry.md
  G8:
    requires:
    - type: csv_nonempty_rows
      path: evidence/evidence_ledger.csv
      min_rows: 1
    - type: markdown_nonplaceholder_lines
      path: paper/draft.md
      min_lines: 1
  G9:
    requires:
    - type: file_not_placeholder
      path: code/99_make_all.py
      marker: Project master script placeholder
    - type: result_index_all_have_provenance
      path: evidence/result_index.csv
layers:
  research_judgment:
    required_files:
    - discovery/idea_memo.md
    - discovery/01_literature_scope.md
    - discovery/idea_bank.csv
    - discovery/exploration_policy.md
    - discovery/literature/synthesis/literature_map.md
    - discovery/literature/paper_registry.csv
    - discovery/literature/citation_audit.md
    - discovery/data_inventory.csv
    - discovery/feasibility_matrix.md
    - discovery/feasibility_memo.md
    - discovery/design_sketch.md
    - discovery/PROMOTE_TO_HARNESS.md
    - docs/method_card.md
    - evidence/claim_registry.md
    - decisions/decision_log.md
    - decisions/revision_log.md
  agent_execution:
    required_dirs:
    - tasks
    - agent_runs
    - audits
  mechanical_verification:
    required_dirs:
    - checks
  harness:
    required_files:
    - harness/permissions.yml
    - harness/protocols/worker_protocol.md
    - harness/protocols/critic_protocol.md
    - harness/protocols/human_gate.md
    - harness/protocols/full_run_checklist.md
    - harness/agent_roles.yml
    - harness/skill_registry.md
    - harness/skill_invocation_rules.md
    - harness/practical_skill_menu.md
    - harness/skill_map_core.yml
    - harness/skill_map_reference.md
  stage_agents:
    required_files:
    - AGENTS.md
    - discovery/AGENTS.md
    - discovery/literature/AGENTS.md
    - execution/AGENTS.md
protected_files:
- docs/protected_definitions.yml
- docs/data_contract.yml
- evidence/claim_registry.md
- harness/permissions.yml
never_modify_without_human_approval:
- data/raw/
- docs/protected_definitions.yml
default_task_policy:
  raw_data_write_access: false
  protected_definition_changes: requires explicit human approval
  claim_strengthening: requires evidence and claim registry update
  preferred_spec_selection: must not be based on significance alone
checks:
  correction_ledger: checks/check_correction_ledger.py
  discovery_completeness: checks/check_discovery_completeness.py
  gate_exit: checks/check_gate_exit.py
  idea_bank: checks/check_idea_bank.py
  stage_agents: checks/check_stage_agents.py
  skill_layer: checks/check_skill_layer.py
  feasibility_matrix: checks/check_feasibility_matrix.py
  literature_tools: checks/check_literature_tools.py
  framing_deck: checks/check_framing_deck.py
  literature_registry: checks/check_literature_registry.py
  literature_functions: checks/check_literature_functions.py
  citation_audit: checks/check_citation_audit.py
  anchors_in_registry: checks/check_anchors_in_registry.py
  git_guardrails: checks/check_git_guardrails.py
  data_inventory: checks/check_data_inventory.py
  data_diagnostics: checks/check_data_diagnostics.py
  design_options: checks/check_design_options.py
  design_selection: checks/check_design_selection.py
  variable_construction: checks/check_variable_construction.py
  data_contract: checks/check_data_contract.py
  protected_definitions: checks/check_protected_definitions.py
  claim_registry: checks/check_claim_registry.py
  claim_ceiling: checks/check_claim_ceiling.py
  claim_method_consistency: checks/check_claim_method_consistency.py
  paper_numbers: checks/check_paper_numbers.py
  output_reproducibility: checks/check_output_reproducibility.py
  project_status: checks/check_project_status.py
  provenance: checks/check_provenance.py
  task_contract: checks/check_task_contract.py
  agent_run_report: checks/check_agent_run_report.py
  agent_runs_tools: checks/check_agent_runs_tools.py
  pipeline_runs: checks/check_pipeline_runs.py
  replication_package: checks/check_replication_package.py


When done, the file(s) above must pass the AEROS checks. Do not explain; just produce conformant files.
```
