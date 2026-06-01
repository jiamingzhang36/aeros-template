#!/usr/bin/env python3
from __future__ import annotations
import csv, json, hashlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
IN=ROOT/'outputs/audit_runs/manual_ai_outputs.jsonl'
SUMMARY=ROOT/'outputs/tables/pilot_measurement_summary.csv'
ROBUST=ROOT/'outputs/tables/pilot_robustness_summary.csv'
PROV=ROOT/'outputs/.provenance'
RESULT_INDEX=ROOT/'evidence/result_index.csv'
CLAIMS=ROOT/'evidence/claim_registry.md'

BUDGETS={'low_income_snap':85.0,'moderate_budget':120.0}

def sha(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def rows():
    return [json.loads(line) for line in IN.read_text().splitlines() if line.strip()]

def write_prov(result_id,path,desc):
    PROV.mkdir(parents=True,exist_ok=True)
    (PROV/f'{result_id}.json').write_text(json.dumps({
        'result_id':result_id,'output_path':str(path.relative_to(ROOT)),
        'created_at':datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'script_or_source':'code/02_analysis/analyze_pilot_outputs.py',
        'sha256':sha(path),'inputs':['outputs/audit_runs/prompt_grid.csv','outputs/audit_runs/manual_ai_outputs.jsonl'],
        'claim_boundary':'pilot current-Codex-session outputs only; not platform-wide evidence'
    },indent=2),encoding='utf-8')

def main():
    data=rows(); SUMMARY.parent.mkdir(parents=True,exist_ok=True)
    byp=defaultdict(list)
    for r in data: byp[r['persona']].append(r)
    with SUMMARY.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['persona','runs','mean_affordability_ratio','max_affordability_ratio','mean_vague_items','mean_nutrition_flags','within_budget_share'])
        w.writeheader()
        for persona,rs in sorted(byp.items()):
            budget=BUDGETS[persona]
            ratios=[r['estimated_cost']/budget for r in rs]
            w.writerow({'persona':persona,'runs':len(rs),'mean_affordability_ratio':round(sum(ratios)/len(ratios),3),'max_affordability_ratio':round(max(ratios),3),'mean_vague_items':round(sum(r['vague_items'] for r in rs)/len(rs),3),'mean_nutrition_flags':round(sum(r['nutrition_flags'] for r in rs)/len(rs),3),'within_budget_share':round(sum(r['estimated_cost']<=budget for r in rs)/len(rs),3)})
    bypv=defaultdict(list)
    for r in data: bypv[(r['persona'],r['prompt_variant'])].append(r)
    with ROBUST.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['persona','prompt_variant','runs','mean_affordability_ratio','mean_nutrition_flags'])
        w.writeheader()
        for (persona,variant),rs in sorted(bypv.items()):
            budget=BUDGETS[persona]
            w.writerow({'persona':persona,'prompt_variant':variant,'runs':len(rs),'mean_affordability_ratio':round(sum(r['estimated_cost']/budget for r in rs)/len(rs),3),'mean_nutrition_flags':round(sum(r['nutrition_flags'] for r in rs)/len(rs),3)})
    write_prov('R002',SUMMARY,'Pilot measurement summary from current Codex-session AI grocery outputs.')
    write_prov('R003',ROBUST,'Prompt-variant robustness summary for pilot current Codex-session outputs.')
    fieldnames=['result_id','output_type','path','script_or_source','description','created_date','linked_claims','notes']
    existing=[]
    if RESULT_INDEX.exists():
        with RESULT_INDEX.open(newline='',encoding='utf-8') as f:
            existing=[r for r in csv.DictReader(f) if r.get('result_id') not in {'R002','R003'}]
    today=datetime.now(timezone.utc).date().isoformat()
    existing += [
        {'result_id':'R002','output_type':'table','path':'outputs/tables/pilot_measurement_summary.csv','script_or_source':'code/02_analysis/analyze_pilot_outputs.py','description':'Pilot measurement summary for current Codex-session AI grocery recommendation outputs.','created_date':today,'linked_claims':'C002','notes':'Pilot only; current Codex session; not platform-wide evidence.'},
        {'result_id':'R003','output_type':'table','path':'outputs/tables/pilot_robustness_summary.csv','script_or_source':'code/02_analysis/analyze_pilot_outputs.py','description':'Prompt-variant robustness summary for pilot current Codex-session outputs.','created_date':today,'linked_claims':'C002','notes':'Pilot robustness only; not final robustness suite.'},
    ]
    with RESULT_INDEX.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fieldnames); w.writeheader(); w.writerows(existing)
    CLAIMS.write_text('''# Claim Registry\n\n## Claim Types\n\n- descriptive\n- measurement\n- associational\n- causal\n- mechanism\n- external-validity\n- policy-translation\n- forecast\n\n## Registry\n\n| Claim ID | Claim | Type | Status | Evidence ID(s) | Result ID(s) | Boundary / Limitation | Approved |\n|---|---|---|---|---|---|---|---|\n| C001 | The execution pipeline can produce a bounded measurement summary for an AI grocery recommendation audit using the selected O1 design. | descriptive | retired |  | R001 | Smoke validation only; retired before claim approval because R002/R003 supersede it for pilot validation. | no |\n| C002 | In a small current-Codex-session pilot, the audit pipeline measured affordability, vagueness, and nutrition-flag summaries across low-income SNAP-relevant and moderate-budget personas. | measurement | ambiguous |  | R002;R003 | Pilot outputs from this Codex session only; not evidence about deployed AI systems, all models, or real consumers. | no |\n\n## Status Values\n\n- draft\n- supported\n- ambiguous\n- unsupported\n- retired\n\n## Rules\n\n- A claim cannot be marked supported without at least one evidence ID or result ID.\n- A causal claim requires a method card that supports causal language.\n- A forecast claim requires explicit forecast validation or must remain unsupported.\n- Policy translation must stay within the protected sample, geography, period, and outcome definitions.\n''',encoding='utf-8')
    print(f'wrote {SUMMARY}')
    print(f'wrote {ROBUST}')

if __name__=='__main__': main()
