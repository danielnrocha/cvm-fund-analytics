"""Isolated integration replay: delta captures, old-date corrections, A/B/A and rebuild."""
from pathlib import Path
import sys
import csv,json,os,shutil,subprocess,tempfile
import duckdb
ROOT=Path(__file__).resolve().parents[1];DBT=ROOT/'compatibility/dbt-v2-metricflow/.venv-dbt/bin/dbt'
sys.path.insert(0,str(ROOT/'tests/ingestion'))
from fixture_loader import load as load_sources
E=ROOT/'transform/evidence';results=[]
with tempfile.TemporaryDirectory(prefix='cvm-history-') as tmp:
    p=Path(tmp)/'transform';shutil.copytree(ROOT/'transform',p,ignore=shutil.ignore_patterns('target','logs','evidence','*.duckdb*'))
    (p/'seeds').mkdir(exist_ok=True) # Git does not retain empty fixture directories.
    env={**os.environ,'DBT_SEND_ANONYMOUS_USAGE_STATS':'false','DBT_PROFILES_DIR':str(p),'CVM_DB_PATH':str(p/'history.duckdb')}
    def write(name,header,rows):
        with (p/'seeds'/name).open('w',newline='') as f:
            w=csv.writer(f);w.writerow(header);w.writerows(rows)
    write('entities.csv',['cnpj','entity_id','classification_at_capture'],[['00000000000100','CVM:CLASS:A','RF']])
    write('report_calendar.csv',['report_date'],[['2026-04-01'],['2026-04-02']])
    header=['capture_id','source_id','kind','cnpj','subclass','report_date','pl','subscriptions','redemptions','quota','total_assets','investors']
    observations=[];captures=[]
    def build(label,full=False):
        load_sources(p,p/'history.duckdb')
        run=subprocess.run([str(DBT),'build','--profiles-dir',str(p),*(['--full-refresh'] if full else [])],cwd=p,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        (E/f'history-{label}.log').write_text(run.stdout);assert run.returncode==0,run.stdout[-3000:]
    for i,pl in enumerate(['100.00','105.00','100.00'],1):
        row=[f'v{i}',f's{i}','CLASSES - FIF','00000000000100','','2026-04-01',pl,'10.00','0.00','1.00',pl,2]
        observations.append(row);captures.append([f'v{i}',f'2026-10-0{i} 12:00:00'])
        write('observations.csv',header,[row]);write('captures.csv',['capture_id','captured_at'],captures)
        build(str(i))
        with duckdb.connect(str(p/'history.duckdb'),read_only=True) as c:
            n=c.execute('select count(*) from sat_daily_report').fetchone()[0]
            assert n==i, f'Capture {i}: expected {i} preserved versions, got {n}'
            assert str(c.execute('select pl from current_daily').fetchone()[0])==pl
        results.append({'capture':i,'versions':n})
    build('replay')
    with duckdb.connect(str(p/'history.duckdb'),read_only=True) as c:
        assert c.execute('select count(*) from sat_daily_report').fetchone()[0]==3
        before=c.execute('select capture_id,pl from sat_daily_report order by captured_at').fetchall()
    write('observations.csv',header,observations)
    build('rebuild',full=True)
    with duckdb.connect(str(p/'history.duckdb'),read_only=True) as c:
        assert c.execute('select capture_id,pl from sat_daily_report order by captured_at').fetchall()==before
(E/'history-results.json').write_text(json.dumps({'captures':results,'replay':True,'rebuild':True},indent=2)+'\n')
print('Delta A/B/A, replay and rebuild PASS')
