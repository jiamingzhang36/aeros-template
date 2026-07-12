#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys, tempfile
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from aeros.runtime.census_probe import run_census_probe
from aeros.runtime.fred_probe import run_fred_probe
from aeros.runtime.economic_probe import compile_official_probe_action

def main()->int:
    failures=[]
    with tempfile.TemporaryDirectory(prefix='aeros_census_probe_') as raw:
        root=Path(raw); (root/'docs').mkdir()
        contract={'economic_data_series':[{'series_id':'pop','provider':'census','provider_native_id':'acs/acs5','release':'2024','variables':[{'id':'B01003_001E','role':'outcome'}],'units':'persons','source_terms':'https://www.census.gov/data/developers/about/terms-of-service.html','geography':{'for':'state:*'},'join_keys':['state'],'minimum_coverage':2,'maximum_missingness':0.0}]}
        (root/'docs/data_contract.yml').write_text(yaml.safe_dump(contract),encoding='utf-8')
        data=json.dumps([['NAME','B01003_001E','state'],['Alabama','5108468','01'],['Alaska','733406','02']]).encode(); metadata=json.dumps({'variables':{'B01003_001E':{'label':'Estimate!!Total:','concept':'TOTAL POPULATION','predicateType':'int'}}}).encode()
        def fetch(url:str)->bytes: return metadata if '/variables/' in url else data
        report=run_census_probe(root,fetch=fetch)
        if report['status']!='PASS' or report['probe']['rows']!=2 or report['probe']['missing_join_keys']: failures.append('valid bounded Census contract did not pass')
        report_path=root/report['artifacts']['report']; prov=json.loads((root/report['artifacts']['provenance']).read_text())
        if prov['artifact_sha256']!=hashlib.sha256(report_path.read_bytes()).hexdigest(): failures.append('provenance hash does not match final probe report')
        if prov.get('admission_status')!='nonproduction_probe': failures.append('probe provenance crossed promotion boundary')
        try: compile_official_probe_action(root,api_key_env='AEROS_FIXTURE_MISSING_CENSUS_KEY')
        except PermissionError as exc:
            if 'blocked_missing_credentials' not in str(exc): failures.append('Census missing-key blocker is not explicit')
        else: failures.append('Census ActionSpec compiled without required API credential')
        contract['economic_data_series'][0]['join_keys']=['county']; (root/'docs/data_contract.yml').write_text(yaml.safe_dump(contract),encoding='utf-8')
        if run_census_probe(root,fetch=fetch)['status']!='FAIL': failures.append('missing join key did not fail probe')
        fred={'economic_data_series':[{'series_id':'gdp','provider':'fred','provider_native_id':'GDP','release':'current_release','frequency':'quarterly','units':'billions','source_terms':'https://fred.stlouisfed.org/legal/','observation_start':'2020-01-01','observation_end':'2020-07-01','join_keys':['observation_date'],'minimum_coverage':3,'maximum_missingness':0.0}]}; (root/'docs/data_contract.yml').write_text(yaml.safe_dump(fred),encoding='utf-8')
        fred_csv=b'observation_date,GDP\n2020-01-01,1\n2020-04-01,2\n2020-07-01,3\n'
        fred_report=run_fred_probe(root,fetch=lambda _url:fred_csv)
        if fred_report['status']!='PASS' or fred_report['economic_data_series']['units_verification']!='contract_declared_not_provider_verified_without_FRED_API_key': failures.append('bounded FRED probe did not preserve unit-verification boundary')
        duplicate=b'observation_date,GDP\n2020-01-01,1\n2020-01-01,2\n2020-07-01,3\n'
        if run_fred_probe(root,fetch=lambda _url:duplicate)['status']!='FAIL': failures.append('duplicate FRED join key did not fail probe')
        spec=compile_official_probe_action(root)
        if spec.runtime_profile!='isolated-official-economic-probe' or len(spec.expected_outputs)!=3: failures.append('official probe did not compile an exact isolated ExecutionEnvelope')
    if failures:
        print('FAIL: Census probe'); [print('- '+x) for x in failures]; return 1
    print('PASS: Census/FRED DataContract probes pin provider/release and verify bounded coverage, missingness, join keys, artifacts, provenance, and unit boundaries')
    return 0
if __name__=='__main__': raise SystemExit(main())
