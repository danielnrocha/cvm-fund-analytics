"""Reproduce external JSON staging and inspect actual dbt column-lineage edges."""
import json, os, subprocess, hashlib
from pathlib import Path
from decimal import Decimal
import duckdb
P=Path(__file__).resolve().parent
os.chdir(P)
env=os.environ.copy();env['DBT_SEND_ANONYMOUS_USAGE_STATS']='false'
prefix=['/usr/bin/sandbox-exec','-f','network-deny.sb']
def run(name,args,sandbox=True):
 p=subprocess.run((prefix if sandbox else [])+args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
 Path('evidence/'+name+'.log').write_text(p.stdout)
 assert p.returncode==0,p.stdout
# Preserve a reproducible negative control: direct reader works at runtime but fails strict analysis.
experiment=Path('models/external_json_probe.sql')
assert not experiment.exists()
try:
 experiment.write_text(Path('experiments/external_json_probe.sql').read_text())
 negative=subprocess.run(prefix+['.venv-dbt/bin/dbt','build','--profiles-dir','.','--select','external_json_probe','--static-analysis','strict'],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=60)
 Path('evidence/20-external-json.log').write_text(negative.stdout)
 assert negative.returncode!=0 and 'Unresolved identifier format' in negative.stdout,negative.stdout
 run('21-external-json-runtime',['.venv-dbt/bin/dbt','build','--profiles-dir','.','--select','external_json_probe','--static-analysis','off'])
 with duckdb.connect('probe.duckdb',read_only=True) as check:
  assert check.execute('select event_id, revenue from external_json_probe order by event_id').fetchall()==[('a',Decimal('125.50')),('b',None),('c',None)]
finally:
 experiment.unlink()
run('26-load-landing',['.venv-mf/bin/python','load_json_fixture.py'])
run('27-build-strict',['.venv-dbt/bin/dbt','build','--profiles-dir','.','--static-analysis','strict','--generate-info-schema'])
run('28-docs-column-lineage',['.venv-mf/bin/python','pinned_docs.py'],sandbox=False)
c=duckdb.connect('probe.duckdb',read_only=True)
rows=c.execute('select event_id,revenue,tag_count,rejection_reason from stg_external_json order by line_number').fetchall()
assert rows==[('a',Decimal('125.50'),2,None),('b',None,0,None),('c',None,0,'invalid_revenue'),(None,None,0,'malformed_json')],rows
raw=Path('fixtures/external.jsonl').read_text()
assert c.execute('select payload from raw_json_fixture order by line_number').fetchall()==[(x,) for x in raw.splitlines()]
assert c.execute("select count(*) from raw_json_fixture where payload like '%new_field%'").fetchone()==(1,)
assert c.execute('select distinct file_sha256 from raw_json_fixture').fetchone()==(hashlib.sha256(raw.encode()).hexdigest(),)
edges=c.execute("select parent_node_unique_id,parent_column_name,child_node_unique_id,child_column_name,evolution from read_parquet('target/info_schema/v1/dbt.column_lineage.parquet') order by 1,2,3,4").fetchall()
assert any(e[0]=='seed.compatibility_probe.shipments' and e[1]=='revenue' and e[2]=='model.compatibility_probe.fct_shipments' and e[3]=='revenue' for e in edges)
assert any(e[0]=='source.compatibility_probe.fixture_landing.raw_json_fixture' and e[1]=='payload' and e[2]=='model.compatibility_probe.stg_external_json' and e[3]=='revenue' for e in edges),edges
Path('evidence/extended-results.json').write_text(json.dumps({'passed':True,'checks':['nested_json','decimal','null','empty_array','missing_array','unknown_field_preserved','invalid_numeric_quarantined','malformed_json_quarantined','all_raw_lines_preserved','file_checksum','strict_build','offline_docs','seed_column_edge','source_payload_column_edge'],'rows':rows,'column_lineage_edges':edges},indent=2,default=str)+'\n')
print('14 extended checks passed; column edges:',len(edges))
