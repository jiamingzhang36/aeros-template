# NEXT_ACTION

recommended_next_action: Adopt or enter a research idea before running lane tasks.
why_this_next: No research topic/question is recorded yet, so running data, literature, or writing tasks would be route churn.
lane: discovery
status_label: ROUTE_READY
command: python3 -m aeros.cli adopt --idea "<your research idea>" --dry-run
stop_condition: Stop after the adoption preview shows the candidate gate, gap plan, and next discovery route.
source: project_manifest.yml
blocked: False

This is a deterministic recommendation. It does not execute tasks, approve gates, or certify research substance.