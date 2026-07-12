from __future__ import annotations
from pathlib import Path
from typing import Any
from hashlib import sha256
import os
import yaml

from .action_spec import ActionSpec
from .execution_envelope import ExecutionEnvelope

def _selected(root:Path, series_id:str, contract_path:str)->dict[str,Any]:
    data=yaml.safe_load((root/contract_path).read_text(encoding='utf-8')) or {}; rows=[r for r in data.get('economic_data_series') or [] if isinstance(r,dict)]
    if series_id!='auto': rows=[r for r in rows if str(r.get('series_id'))==series_id]
    if not rows: raise ValueError('DataContract has no matching EconomicDataSeries')
    return rows[0]

def run_official_probe(root:Path, *, series_id:str='auto', contract_path:str='docs/data_contract.yml', api_key_env:str='CENSUS_API_KEY')->dict[str,Any]:
    row=_selected(root,series_id,contract_path); provider=str(row.get('provider') or '').lower()
    if provider=='census':
        from .census_probe import run_census_probe
        return run_census_probe(root,series_id=series_id,contract_path=contract_path,api_key_env=api_key_env)
    if provider in {'fred','alfred'}:
        from .fred_probe import run_fred_probe
        return run_fred_probe(root,series_id=series_id,contract_path=contract_path)
    raise ValueError(f'unsupported official probe provider: {provider}')

def compile_official_probe_action(root:Path, *, series_id:str='auto', contract_path:str='docs/data_contract.yml', api_key_env:str='CENSUS_API_KEY')->ActionSpec:
    row=_selected(root,series_id,contract_path); resolved=str(row.get('series_id') or '')
    if str(row.get('provider') or '').lower() == 'census' and not os.environ.get(api_key_env,'').strip():
        raise PermissionError(f'blocked_missing_credentials: Census Data API requires {api_key_env}')
    slug='_'.join(part for part in ''.join(c.lower() if c.isalnum() else '_' for c in resolved).split('_') if part)
    if not slug: raise ValueError('EconomicDataSeries series_id cannot compile to an output slug')
    outputs=(f'data/probes/{slug}/sample.csv',f'data/probes/{slug}/probe.json',f'outputs/.provenance/PROBE_{slug}.json')
    envelope=ExecutionEnvelope(read_roots=('.',),write_roots=(f'data/probes/{slug}/','outputs/.provenance/'),deny_roots=('data/raw/','data/intermediate/','data/processed/','paper/','evidence/claim_registry.md','decisions/approvals/'),expected_outputs=outputs,runtime_profile='isolated-official-economic-probe')
    command=f'python3 -m aeros.cli data probe official --series-id {resolved} --contract {contract_path} --api-key-env {api_key_env} --json'
    digest=sha256(command.encode()).hexdigest()[:12]
    return ActionSpec(id=f'AS-{digest}',kind='official_economic_probe',lane='data',effect_class='local_write_preview',capabilities=('read_data_contract','network_official_source','write_nonproduction_probe'),expected_outputs=outputs,acceptance_checks=('checks/check_census_probe.py',),command=command,stop_condition='bounded probe artifacts and provenance accepted without canonical admission',runtime_profile=envelope.runtime_profile,execution_envelope=envelope.to_dict(),authority_boundary={'claim':'none','canonical':'none','release':'none','credentials':'environment_only','human_decision_required':'false'},does_not_prove=('canonical admission','construct validity','identification validity','claim support'))
