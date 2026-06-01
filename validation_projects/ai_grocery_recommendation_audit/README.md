# AI Grocery Recommendation Audit Validation Project

This instantiated AEROS validation project tests the idea-to-paper automation loop on an algorithm-audit food policy project.

## Source memo

- Original DOCX: `discovery/intake/AI_Grocery_Recommendation_Audit_Research_Demo.docx`
- Extracted text: `discovery/intake/source_memo_extracted.txt`
- Seed idea: `discovery/intake/idea_seed.txt`

## Initial research idea

We audit whether AI-generated grocery recommendations are stable, affordable, nutritionally reasonable, and equitable across realistic household constraints, with special attention to low-income and SNAP-relevant food choice environments.

## AEROS usage

Preview the next gate:

```bash
PYTHONPATH=/Users/jiamingzhang/aeros-template python3 -m aeros.cli iterate --dry-run --to-next-gate
```

Run the next automated gate loop only when ready to invoke agents:

```bash
PYTHONPATH=/Users/jiamingzhang/aeros-template python3 -m aeros.cli iterate --to-next-gate
```

This folder is a validation project. Do not copy its data, outputs, run reports, or state back into the root AEROS template unless converting a behavior into a generic template improvement.
