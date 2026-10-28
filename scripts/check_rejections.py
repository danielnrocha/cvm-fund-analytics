"""Negative gates execute real dbt builds on an isolated project."""
from pathlib import Path
import sys
import csv,os,shutil,subprocess,tempfile,json
import duckdb
ROOT=Path(__file__).resolve().parents[1];P=ROOT/'transform';E=P/'evidence';DBT=ROOT/'compatibility/dbt-v2-metricflow/.venv-dbt/bin/dbt'
sys.path.insert(0,str(ROOT/'tests/ingestion'))
from fixture_loader import load as load_sources
results=[]
with tempfile.TemporaryDirectory(prefix='cvm-gates-') as tmp:
    p=Path(tmp)/'transform';shutil.copytree(P,p,ignore=shutil.ignore_patterns('target','logs','evidence','*.duckdb*'))
    (p/'seeds').mkdir(exist_ok=True) # Git does not retain empty fixture directories.
    env={**os.environ,'DBT_PROFILES_DIR':str(p),'CVM_DB_PATH':str(p/'gate.duckdb'),'DBT_SEND_ANONYMOUS_USAGE_STATS':'false'}
    def write(name,header,rows):
        with (p/'seeds'/name).open('w',newline='') as f:w=csv.writer(f);w.writerow(header);w.writerows(rows)
    write('entities.csv',['cnpj','entity_id','classification_at_capture'],[['00000000000100','CVM:CLASS:A','RF']])
    write('report_calendar.csv',['report_date'],[['2026-04-01']])
    write('captures.csv',['capture_id','captured_at'],[['v1','2026-10-01 12:00:00']])
    header=['capture_id','source_id','kind','cnpj','subclass','report_date','pl','subscriptions','redemptions','quota','total_assets','investors']
    base=['v1','s1','CLASSES - FIF','00000000000100','','2026-04-01','100.00','10.00','0.00','1.00','100.00','2']
    def build(name):
        load_sources(p,p/'gate.duckdb')
        run=subprocess.run([str(DBT),'build','--profiles-dir',str(p)],cwd=p,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (E/f'rejection-{name}.log').write_text(run.stdout);return run
    write('observations.csv',header,[base]);assert build('baseline').returncode==0
    def state():
        with duckdb.connect(str(p/'gate.duckdb'),read_only=True) as c:
            return {t:c.execute(f'select * from {t} order by all').fetchall() for t in ['sat_daily_report','current_daily','fct_daily']}
    baseline=state()
    for name,col,value in [('null-kind',2,''),('null-pl',6,''),('orphan-capture',0,'absent'),('changed-replay',6,'999.00'),('outside-calendar',5,'2026-04-02')]:
        row=base.copy();row[col]=value;write('observations.csv',header,[row])
        run=build(name)
        nodes=json.loads((p/'target/run_results.json').read_text())['results']
        downstream={r['unique_id'].split('.')[-1]:r['status'] for r in nodes if r['unique_id'] in ('model.cvm_demo.current_daily','model.cvm_demo.fct_daily')}
        gate_failed=any(r['unique_id'].startswith('test.') and r['status'] in ('fail','error') for r in nodes)
        results.append({'case':name,'blocked':run.returncode!=0 and gate_failed and set(downstream.values())=={'skipped'} and len(downstream)==2 and state()==baseline})
    (E/'rejection-results.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(r['blocked'] for r in results),results
print('Required fields, capture FK and immutable replay gates PASS')
