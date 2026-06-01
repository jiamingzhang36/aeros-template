# Table outputs

Place table-generating scripts and notebooks in this folder.

All scripts that emit analysis tables should call the shared provenance helper:

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

# after the table is written to output_path
record = write_provenance_record(
    output_path=output_path,
    script_or_source=Path(__file__).name,
    output_type="table",
    description="descriptive label",
    input_paths=[input_csv, config_path],
    parameters={"n_rows": 10},
)
print(record["result_id"], record["provenance_path"])
```

Keep generated provenance under `outputs/.provenance/<result_id>.json`.
