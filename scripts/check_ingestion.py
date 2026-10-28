"""Clean-database ingestion, immutable replay, dbt and MetricFlow acceptance."""
from pathlib import Path
import os,subprocess,tempfile,json
import duckdb
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'transform';E=P/'evidence/ingestion'
PYTHON=ROOT/'compatibility/dbt-v2-metricflow/.venv-mf/bin/python';DBT=ROOT/'compatibility/dbt-v2-metricflow/.venv-dbt/bin/dbt'
with tempfile.TemporaryDirectory(prefix='cvm-clean-ingestion-') as tmp:
 db=Path(tmp)/'clean.duckdb'
 env={**os.environ,'CVM_DB_PATH':str(db),'DBT_PROFILES_DIR':str(P),'DBT_SEND_ANONYMOUS_USAGE_STATS':'false'}
 def run(name,args):
  result=subprocess.run(args,cwd=P,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
  (E/f'clean-{name}.log').write_text(result.stdout);assert result.returncode==0,result.stdout[-3500:]
  return result.stdout
 first=json.loads(run('load',[str(PYTHON),str(ROOT/'scripts/ingest_cvm.py')]))
 second=json.loads(run('replay',[str(PYTHON),str(ROOT/'scripts/ingest_cvm.py')]))
 assert first['inserted'] and not second['inserted']
 run('build',[str(DBT),'build','--profiles-dir',str(P)])
 run('oracles',[str(PYTHON),str(ROOT/'scripts/check_real_oracles.py')])
 run('semantic',[str(PYTHON),str(ROOT/'scripts/check_semantics.py')])
 with duckdb.connect(str(db),read_only=True) as c:
  assert c.execute('select count(*) from quarantine').fetchone()[0]==0
  assert c.execute('select count(*) from landing.raw_envelopes').fetchone()[0]==7554
  counts=c.execute('select sum(accepted),sum(rejected),sum(excluded),sum(source_records),bool_and(balanced) from audit_ingestion_files').fetchone()
  assert counts==(7554,0,3220430,3227984,True),counts
 (E/'clean-results.json').write_text(json.dumps({'fresh_database':True,'replay':True,'accepted':7554,'rejected':0,'excluded':3220430,'source_records':3227984,'oracles_and_metricflow':True},indent=2)+'\n')
print('Clean database, immutable replay, reconciliation and real semantic oracles PASS')
