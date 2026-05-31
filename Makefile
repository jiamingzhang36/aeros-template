.PHONY: all checks pipeline clean-logs lock-definitions index-agent-runs promote-discovery-execution

all: pipeline checks

pipeline:
	python3 code/99_make_all.py

checks:
	python3 checks/build_agent_runs_index.py
	python3 checks/run_harness_checks.py

index-agent-runs:
	python3 checks/build_agent_runs_index.py

lock-definitions:
	python3 - <<'PY'
from pathlib import Path

path = Path("docs/protected_definitions.yml")
text = path.read_text(encoding="utf-8")
text = text.replace('status: "draft"', 'status: "locked"')
text = text.replace("status: 'draft'", "status: 'locked'")
path.write_text(text, encoding="utf-8")
print("Updated docs/protected_definitions.yml: status -> locked")
PY

clean-logs:
	find outputs/logs -type f -name "*.log" -delete

promote-discovery-execution:
	python3 checks/create_promotion_tag.py --from-stage discovery --to-stage execution
