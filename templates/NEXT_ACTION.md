# NEXT_ACTION

recommended_next_action: The deterministic next step AEROS recommends.
why_this_next: Why this step outranks checks, human gates, data, literature, analysis, claim, writing, or compliance alternatives.
lane: data | literature | analysis | claim | writing | compliance | harness | human_gate | discovery | project
status_label: CHECK_PASS | CAPTURE_LOGGED | ROUTE_READY | SUBSTANTIVE_PRODUCED
command: The next command to run, or the human decision needed.
stop_condition: The exact condition where Codex must stop rather than drift into another lane.
source: deterministic
blocked: false

## ActionSpec

action_spec_id: AS-...
action_spec_kind: adopt_idea | data_scan | literature_status | iterate_preview | check_profile | human_decision
action_spec_effect_class: read_only | local_write_preview | local_write | task_run | human_decision | blocked
action_spec_capabilities: [read_project_state]
action_spec_requires_decision: false
action_spec_producer_mode: declared
action_spec_expected_outputs: []
action_spec_acceptance_checks: []
action_spec_resource_budget: {max_provider_calls: "0", max_cost_usd: "0"}

This is a recommendation, not an execution record, gate approval, or claim-support artifact. The ActionSpec is the typed control record; the command is a compatibility preview and must not be treated as authority by itself.
