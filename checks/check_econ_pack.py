#!/usr/bin/env python3
"""Exercise the economics object chain, protocols, radar, jobs, and scorecard."""
from __future__ import annotations
import csv, json, subprocess, sys, tempfile
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from aeros.runtime.econ_pack import build_literature_radar, build_skill_scorecard, compile_drive_job, compile_protocol, initialize_registries, submission_review_ready, validate_object_chain
from aeros.runtime.drive import build_drive_report

def write(path:Path, fields:list[str], rows:list[dict[str,str]])->None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',newline='',encoding='utf-8') as h:
        w=csv.DictWriter(h,fieldnames=fields); w.writeheader(); w.writerows(rows)

def main()->int:
    failures=[]
    with tempfile.TemporaryDirectory(prefix='aeros_econ_pack_') as raw:
        root=Path(raw); initialize_registries(root); base=root/'evidence/econ'
        write(base/'sample_registry.csv',['sample_id','dataset_snapshot_ids','population','time_window','filters','n_expected','status'],[{'sample_id':'S1','dataset_snapshot_ids':'D1','population':'units','time_window':'2020','filters':'none','n_expected':'10','status':'accepted'}])
        write(base/'specification_registry.csv',['spec_id','estimand_id','sample_id','outcome','treatment','controls','fixed_effects','cluster','weights','window','estimator','software','package_versions','protocol','status'],[{'spec_id':'SP1','estimand_id':'E1','sample_id':'S1','outcome':'y','treatment':'d','controls':'x','fixed_effects':'unit','cluster':'unit','weights':'none','window':'2020','estimator':'ols','software':'python','package_versions':'fixture','protocol':'panel','status':'registered'}])
        (root/'evidence').mkdir(exist_ok=True); (root/'evidence/result_index.csv').write_text('result_id,output_type,path,script_or_source,description,created_date,linked_claims,notes\nR1,table,out.csv,run.py,x,2026-07-11,C1,\n',encoding='utf-8'); (root/'evidence/claim_registry.md').write_text('| Claim ID | Status |\n|---|---|\n| C1 | active |\n',encoding='utf-8')
        write(base/'exhibit_registry.csv',['exhibit_id','result_id','spec_id','artifact_path','cell_or_panel','status'],[{'exhibit_id':'X1','result_id':'R1','spec_id':'SP1','artifact_path':'table.tex','cell_or_panel':'1','status':'bound'}])
        write(base/'sentence_binding_registry.csv',['sentence_id','manuscript_path','sentence_locator','exhibit_id','result_id','claim_id','status'],[{'sentence_id':'M1','manuscript_path':'paper.tex','sentence_locator':'1','exhibit_id':'X1','result_id':'R1','claim_id':'C1','status':'bound'}])
        if validate_object_chain(root)['status']!='PASS': failures.append('complete Sample-to-Claim chain failed')
        (root/'evidence/claim_registry.md').write_text('| Claim ID | Status |\n|---|---|\n| C10 | active |\n',encoding='utf-8')
        if validate_object_chain(root)['status']!='FAIL': failures.append('claim C1 falsely resolved through substring C10')
        (root/'evidence/claim_registry.md').write_text('| Claim ID | Status |\n|---|---|\n| C1 | active |\n',encoding='utf-8')
        text=(base/'specification_registry.csv').read_text(encoding='utf-8').replace(',S1,',',MISSING,'); (base/'specification_registry.csv').write_text(text,encoding='utf-8')
        if validate_object_chain(root)['status']!='FAIL': failures.append('broken sample foreign key was not detected')
        for name in ('iv','did','rd','panel','synthetic_control'):
            packet=compile_protocol(name)
            if not packet['machine_diagnostics'] or not packet['human_review']: failures.append(f'{name} protocol is empty')
        write(root/'discovery/literature/paper_registry.csv',['paper_id','title','primary_function','full_text_available','extraction_card','used_in_synthesis','screening_decision'],[
            {'paper_id':'P1','title':'Needed','primary_function':'method','full_text_available':'no','extraction_card':'','used_in_synthesis':'yes','screening_decision':'include'},
            {'paper_id':'P2','title':'Watch','primary_function':'background','full_text_available':'yes','extraction_card':'card','used_in_synthesis':'no','screening_decision':'include'},
            {'paper_id':'P3','title':'Ignore','primary_function':'background','full_text_available':'no','extraction_card':'','used_in_synthesis':'no','screening_decision':'exclude'}])
        radar=build_literature_radar(root)
        if any(radar['counts'].get(k)!=1 for k in ('read_now','watch','ignore_for_this_project')): failures.append('literature radar did not produce three queues')
        receipt=root/'agent_runs/skill_invocations/T1_skill_invocations.yml'; receipt.parent.mkdir(parents=True); receipt.write_text(yaml.safe_dump({'skills_used':['did-checklist'],'verdict':'pass','artifact_acceptance_status':'accepted','runtime_seconds':10,'cost_usd':1,'human_corrections':0,'blockers_resolved':1}),encoding='utf-8')
        cards=build_skill_scorecard(root).get('scorecards') or []
        if not cards or cards[0]['blocker_resolution_rate']!=1: failures.append('skill scorecard did not aggregate observed outcomes')
        receipt.write_text(yaml.safe_dump({'skills_used':['did-checklist'],'verdict':'pass'}),encoding='utf-8')
        empty_card=build_skill_scorecard(root)['scorecards'][0]
        if any(empty_card[key] is not None for key in ('artifact_acceptance_rate','human_correction_rate','blocker_resolution_rate','average_runtime','average_cost')): failures.append('missing skill outcome observations were misrepresented as zero-valued evidence')
        jobs=('find_data','probe_data','run_specification','diagnose_design','read_literature','bind_or_reproduce_paper')
        if any(not compile_drive_job(j).get('command') for j in jobs): failures.append('one or more drive jobs did not compile')
        for job in jobs:
            handled=build_drive_report(root,job=job)
            objective=handled.get('chosen_objective') or {}
            if handled.get('job')!=job or objective.get('objective_id')!=f'econ_job:{job}': failures.append(f'in-process drive handler mismatch for {job}')
        if not submission_review_ready({'status':'ready'},{'recommendation':'ready_for_human_paper_readiness_review','blockers':['release_gate_not_human_approved']}): failures.append('release approval incorrectly blocks entry into human paper review')
        if submission_review_ready({'status':'blocked'},{'recommendation':'ready_for_human_paper_readiness_review'}): failures.append('blocked submission driver incorrectly entered human review')
    # Pure compilation above covers all six jobs. One representative CLI call
    # proves parser/dispatch wiring without paying six process startups in the
    # daily smoke profile.
    cli_job='probe_data'
    proc=subprocess.run([sys.executable,'-m','aeros.cli','drive','--job',cli_job,'--json'],cwd=ROOT,text=True,capture_output=True,timeout=30)
    if proc.returncode or json.loads(proc.stdout).get('job')!=cli_job: failures.append(f'drive --job {cli_job} failed')
    home=subprocess.run([sys.executable,'-m','aeros.cli'],cwd=ROOT,text=True,capture_output=True,timeout=30)
    if home.returncode or 'RUN NOW' not in home.stdout or 'aeros submit' not in home.stdout: failures.append('three-entry home did not render')
    if failures:
        print('FAIL: econ pack'); [print('- '+f) for f in failures]; return 1
    print('PASS: economics object chain, five protocols, radar, six drive jobs, scorecard, and three-entry UX')
    return 0
if __name__=='__main__': raise SystemExit(main())
