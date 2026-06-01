# Figure outputs

Place figure-generating scripts and notebooks in this folder.

Use the shared provenance helper from every reproducible figure script:

- `from pathlib import Path`
- `import sys`
- `from utils.provenance import write_provenance_record`

Typical call pattern:

```python
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from utils.provenance import write_provenance_record

# after the figure is written to figure_path
record = write_provenance_record(
    output_path=figure_path,
    script_or_source=Path(__file__).name,
    output_type="figure",
    description="descriptive label",
    input_paths=[input_csv, config_path],
    parameters={"dpi": 300},
)
print(record["result_id"], record["provenance_path"])
```

Keep generated provenance under `outputs/.provenance/<result_id>.json`.
