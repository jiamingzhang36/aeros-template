# NEXT_ACTION

recommended_next_action: Adopt or enter a research idea before running lane tasks.
why_this_next: No research topic/question is recorded yet, so running data, literature, or writing tasks would be route churn.
lane: discovery
status_label: ROUTE_READY
command: python3 -m aeros.cli adopt --idea "<your research idea>" --dry-run
stop_condition: Stop after the adoption preview shows the candidate gate, gap plan, and next discovery route.
source: project_manifest.yml
blocked: False

## ActionSpec

action_spec_id: AS-template-adopt-idea
action_spec_kind: adopt_idea
action_spec_effect_class: local_write_preview
action_spec_capabilities: ['read_project_state', 'write_candidate_artifact']
action_spec_requires_decision: True
action_spec_producer_mode: declared
action_spec_expected_outputs: ['adoption/', 'decisions/adoption/']
action_spec_acceptance_checks: []
action_spec_resource_budget: {'max_provider_calls': '0', 'max_cost_usd': '0'}

This is a deterministic recommendation. The ActionSpec is the typed control record; the command is a compatibility preview. It does not execute tasks, approve gates, or certify research substance.
