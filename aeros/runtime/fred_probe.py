"""Bounded no-key FRED graph-CSV probe for current-release observations."""
from __future__ import annotations
import csv, io, json, ssl
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import urlopen
import yaml
import re

def _fetch(url:str)->bytes:
    try:
        import certifi; context=ssl.create_default_context(cafile=certifi.where())
    except ImportError: context=ssl.create_default_context()
    with urlopen(url,timeout=30,context=context) as response: return response.read()

def run_fred_probe(root:Path, *, series_id:str='auto', contract_path:str='docs/data_contract.yml', fetch:Callable[[str],bytes]=_fetch)->dict[str,Any]:
    data=yaml.safe_load((root/contract_path).read_text(encoding='utf-8')) or {}; rows=[r for r in data.get('economic_data_series') or [] if isinstance(r,dict) and str(r.get('provider','')).lower() in {'fred','alfred'}]
    if series_id!='auto': rows=[r for r in rows if str(r.get('series_id'))==series_id]
    if not rows: raise ValueError('DataContract has no matching FRED EconomicDataSeries')
    row=rows[0]; required=('series_id','provider_native_id','units','frequency','observation_start','observation_end','join_keys','source_terms'); missing=[k for k in required if not row.get(k)]
    if missing: raise ValueError('EconomicDataSeries missing: '+', '.join(missing))
    native=str(row['provider_native_id']); params={'id':native,'cosd':str(row['observation_start']),'coed':str(row['observation_end'])}; url='https://fred.stlouisfed.org/graph/fredgraph.csv?'+urlencode(params)
    if not re.fullmatch(r'[A-Za-z0-9._-]+',native): raise ValueError('invalid FRED provider_native_id')
    minimum=int(row.get('minimum_coverage') or 1); maximum=float(row.get('maximum_missingness') or 0)
    if minimum < 1 or not 0 <= maximum <= 1: raise ValueError('coverage/missingness thresholds are outside valid ranges')
    raw=fetch(url); reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))); observations=list(reader); headers=list(reader.fieldnames or []); join_keys=[str(x) for x in row['join_keys']]
    missing_join=[k for k in join_keys if k not in headers]; duplicate_join_rows=len(observations)-len({tuple(r.get(k,'') for k in join_keys) for r in observations}) if not missing_join else 0; values=[r.get(native,'') for r in observations]; missing_values=sum(v in {'','.','NA','null'} for v in values); missingness=missing_values/max(1,len(values))
    passed=len(observations)>=minimum and missingness<=maximum and not missing_join and duplicate_join_rows==0 and native in headers
    slug=''.join(c.lower() if c.isalnum() else '_' for c in str(row['series_id'])).strip('_'); out=root/'data/probes'/slug; out.mkdir(parents=True,exist_ok=True); sample=out/'sample.csv'; sample.write_bytes(raw); retrieved=datetime.now(timezone.utc).isoformat(timespec='seconds'); source_hash=sha256(raw).hexdigest(); report_path=out/'probe.json'; provenance=root/'outputs/.provenance'/f'PROBE_{slug}.json'; provenance.parent.mkdir(parents=True,exist_ok=True)
    report={'model':'AEROS-FRED-PROBE-001','status':'PASS' if passed else 'FAIL','generated_at':retrieved,'economic_data_series':{'series_id':row['series_id'],'provider':'fred','provider_native_id':native,'release_or_vintage':str(row.get('release') or 'current_release'),'retrieval_as_of':retrieved,'frequency':row['frequency'],'units':row['units'],'units_verification':'contract_declared_not_provider_verified_without_FRED_API_key','observation_window':[row['observation_start'],row['observation_end']],'join_keys':join_keys,'source_terms':row['source_terms']},'query':{'url':url,'credential_used':False},'probe':{'rows':len(observations),'columns':headers,'coverage':len(observations)-missing_values,'minimum_coverage':minimum,'missingness':missingness,'maximum_missingness':maximum,'missing_join_keys':missing_join,'duplicate_join_rows':duplicate_join_rows,'observed_min_date':observations[0].get('observation_date','') if observations else '','observed_max_date':observations[-1].get('observation_date','') if observations else ''},'artifacts':{'sample':str(sample.relative_to(root)),'source_snapshot_sha256':source_hash,'report':str(report_path.relative_to(root)),'provenance':str(provenance.relative_to(root))},'next_action':('review units against provider metadata, then propose canonical_candidate acquisition' if passed else 'revise FRED series/window/coverage/join-key contract and rerun bounded probe'),'does_not_prove':['provider-verified units without metadata API','vintage history','canonical admission','construct validity','identification validity','claim support']}
    report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); provenance.write_text(json.dumps({'result_id':f'PROBE_{slug}','artifact_path':str(report_path.relative_to(root)),'artifact_sha256':sha256(report_path.read_bytes()).hexdigest(),'source_provider':'Federal Reserve Bank of St. Louis FRED','provider_native_id':native,'source_terms':row['source_terms'],'retrieval_as_of':retrieved,'source_snapshot_sha256':source_hash,'admission_status':'nonproduction_probe'},indent=2)+'\n',encoding='utf-8'); return report
