"""Bounded Census API probe driven by an EconomicDataSeries contract."""
from __future__ import annotations
import csv, json, os, ssl, re
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import urlopen
import yaml

@dataclass(frozen=True)
class CensusSeries:
    series_id:str; provider_native_id:str; release:str; variables:tuple[dict[str,str],...]
    geography_for:str; geography_in:str; join_keys:tuple[str,...]; units:str
    minimum_coverage:int; maximum_missingness:float; source_terms:str

def _contract_series(root:Path, series_id:str='auto', contract_path:str='docs/data_contract.yml')->CensusSeries:
    data=yaml.safe_load((root/contract_path).read_text(encoding='utf-8')) or {}; rows=[r for r in data.get('economic_data_series') or [] if isinstance(r,dict) and str(r.get('provider','')).lower()=='census']
    if series_id!='auto': rows=[r for r in rows if str(r.get('series_id'))==series_id]
    if not rows: raise ValueError('DataContract has no matching Census EconomicDataSeries')
    row=rows[0]; geo=row.get('geography') or {}; variables=row.get('variables') or []
    required=('series_id','provider_native_id','release','units','join_keys','source_terms'); missing=[k for k in required if not row.get(k)]
    if missing or not variables or not geo.get('for'): raise ValueError('EconomicDataSeries missing: '+', '.join(missing+([] if variables else ['variables'])+([] if geo.get('for') else ['geography.for'])))
    native=str(row['provider_native_id']).strip('/'); release=str(row['release']); minimum=int(row.get('minimum_coverage') or 1); maximum=float(row.get('maximum_missingness') or 0)
    if not re.fullmatch(r'[A-Za-z0-9/_-]+',native) or not re.fullmatch(r'\d{4}',release): raise ValueError('invalid Census provider_native_id or release')
    if minimum < 1 or not 0 <= maximum <= 1: raise ValueError('coverage/missingness thresholds are outside valid ranges')
    return CensusSeries(str(row['series_id']),native,release,tuple({str(k):str(v) for k,v in x.items()} for x in variables if isinstance(x,dict)),str(geo['for']),str(geo.get('in') or ''),tuple(str(x) for x in row['join_keys']),str(row['units']),minimum,maximum,str(row['source_terms']))

def _fetch(url:str)->bytes:
    try:
        import certifi
        context=ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        context=ssl.create_default_context()
    with urlopen(url,timeout=30,context=context) as response: return response.read()

def run_census_probe(root:Path, *, series_id:str='auto', contract_path:str='docs/data_contract.yml', api_key_env:str='CENSUS_API_KEY', fetch:Callable[[str],bytes]=_fetch)->dict[str,Any]:
    series=_contract_series(root,series_id,contract_path); key=os.environ.get(api_key_env,'').strip(); variable_ids=[v.get('id','') for v in series.variables if v.get('id')]
    if not key and fetch is _fetch: raise PermissionError(f'blocked_missing_credentials: Census Data API requires {api_key_env}; no key was supplied')
    base=f"https://api.census.gov/data/{series.release}/{series.provider_native_id}"; params={'get':','.join(['NAME']+variable_ids),'for':series.geography_for}
    if series.geography_in: params['in']=series.geography_in
    if key: params['key']=key
    query_url=base+'?'+urlencode(params,safe=':,*')
    raw=fetch(query_url); metadata_chunks=[]; metadata={}
    for variable_id in variable_ids:
        variable_url=base+'/variables/'+variable_id+'.json'+(('?'+urlencode({'key':key})) if key else '')
        chunk=fetch(variable_url); metadata_chunks.append(chunk); item=json.loads(chunk)
        metadata[variable_id]=item.get('variables',{}).get(variable_id,item)
    metadata_raw=b'\n'.join(metadata_chunks); payload=json.loads(raw)
    if not isinstance(payload,list) or len(payload)<2: raise ValueError('Census response has no data rows')
    headers=[str(x) for x in payload[0]]; rows=[dict(zip(headers,map(str,row))) for row in payload[1:]]
    missing_vars=[v for v in variable_ids if v not in headers or v not in metadata]; missing_cells=sum(1 for row in rows for v in variable_ids if row.get(v,'').strip() in {'','null','None'}); missingness=missing_cells/max(1,len(rows)*len(variable_ids)); join_missing=[k for k in series.join_keys if k not in headers]; duplicate_join_rows=len(rows)-len({tuple(row.get(k,'') for k in series.join_keys) for row in rows}) if not join_missing else 0
    passed=not missing_vars and not join_missing and duplicate_join_rows==0 and len(rows)>=series.minimum_coverage and missingness<=series.maximum_missingness
    slug=''.join(c.lower() if c.isalnum() else '_' for c in series.series_id).strip('_'); out=root/'data/probes'/slug; out.mkdir(parents=True,exist_ok=True); sample=out/'sample.csv'
    with sample.open('w',newline='',encoding='utf-8') as h: writer=csv.DictWriter(h,fieldnames=headers); writer.writeheader(); writer.writerows(rows)
    snapshot_hash=sha256(raw).hexdigest(); metadata_hash=sha256(metadata_raw).hexdigest(); generated=datetime.now(timezone.utc).isoformat(timespec='seconds')
    report={'model':'AEROS-CENSUS-PROBE-001','status':'PASS' if passed else 'FAIL','generated_at':generated,'economic_data_series':{'series_id':series.series_id,'provider':'census','provider_native_id':series.provider_native_id,'release':series.release,'variables':list(series.variables),'units':series.units,'units_verification':'contract_declared_with_provider_variable_label_not_provider_unit_field','source_terms':series.source_terms,'geography':{'for':series.geography_for,'in':series.geography_in},'join_keys':list(series.join_keys)},'query':{'url_without_key':base+'?'+urlencode({k:v for k,v in params.items() if k!='key'},safe=':,*'),'credential_used':bool(key),'api_key_env':api_key_env},'probe':{'rows':len(rows),'columns':headers,'coverage':len(rows),'minimum_coverage':series.minimum_coverage,'missingness':missingness,'maximum_missingness':series.maximum_missingness,'missing_variables':missing_vars,'missing_join_keys':join_missing,'duplicate_join_rows':duplicate_join_rows,'variable_metadata':{v:{'label':metadata.get(v,{}).get('label',''),'concept':metadata.get(v,{}).get('concept',''),'predicateType':metadata.get(v,{}).get('predicateType','')} for v in variable_ids}},'artifacts':{'sample':str(sample.relative_to(root)),'source_snapshot_sha256':snapshot_hash,'variables_snapshot_sha256':metadata_hash},'next_action':('review units/construct against provider documentation, then propose canonical_candidate acquisition' if passed else 'revise provider-native variable/geography/threshold/join-key contract and rerun bounded probe'),'does_not_prove':['provider-verified units','canonical admission','construct validity','identification validity','claim support']}
    report_path=out/'probe.json'; provenance=root/'outputs/.provenance'/f"PROBE_{slug}.json"; provenance.parent.mkdir(parents=True,exist_ok=True)
    report['artifacts'].update({'report':str(report_path.relative_to(root)),'provenance':str(provenance.relative_to(root))}); report_path.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    provenance.write_text(json.dumps({'result_id':f'PROBE_{slug}','artifact_path':str(report_path.relative_to(root)),'artifact_sha256':sha256(report_path.read_bytes()).hexdigest(),'source_provider':'U.S. Census Bureau API','provider_native_id':series.provider_native_id,'release':series.release,'source_terms':series.source_terms,'source_snapshot_sha256':snapshot_hash,'retrieved_at':generated,'admission_status':'nonproduction_probe'},indent=2)+'\n',encoding='utf-8'); return report
