"""Small compatibility probe; no production data or services. Run with .venv-mf/bin/python."""
import csv, hashlib, json, os, subprocess
from pathlib import Path
from decimal import Decimal
import duckdb
ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
env=os.environ.copy()
env.update(DBT_PROFILES_DIR=str(ROOT), DBT_SEND_ANONYMOUS_USAGE_STATS='false', DO_NOT_TRACK='1')
PREFIX=['/usr/bin/sandbox-exec','-f',str(ROOT/'network-deny.sb')]
results=[]
def run(name,args,ok=True,sandbox=True):
    p=subprocess.run((PREFIX if sandbox else [])+args,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    (ROOT/'evidence'/f'{name}.log').write_text(p.stdout)
    passed=(p.returncode==0) if ok else (p.returncode!=0)
    results.append(dict(test=name,exit_code=p.returncode,passed=passed))
    print(name,p.returncode,'PASS' if passed else 'FAIL',flush=True)
    if not passed: print(p.stdout[-2500:],flush=True)
    return p
DBT=str(ROOT/'.venv-dbt/bin/dbt');MF=str(ROOT/'.venv-mf/bin/mf')
run('05-network-denied-control',[str(ROOT/'.venv-mf/bin/python'),'-c','import socket; socket.socket().connect(("1.1.1.1",443))'],False)
run('00-load-external-landing',[str(ROOT/'.venv-mf/bin/python'),'load_json_fixture.py'])
run('06-offline-build',[DBT,'build','--profiles-dir','.'])
manifest=ROOT/'target/semantic_manifest.json'
before=hashlib.sha256(manifest.read_bytes()).hexdigest()
run('07-validate',[MF,'validate-configs'])
for name,extra in [('totals',[]),('daily',['--group-by','metric_time__day']),('monthly',['--group-by','metric_time__month']),('regions',['--group-by','shipment__region']),('filtered',['--where',"{{ Dimension('shipment__region') }} = 'NE'"])]:
    run('08-'+name,[MF,'query','--metrics','total_revenue,total_cost,shipment_count,margin_rate',*extra,'--csv',f'evidence/{name}.csv'])
run('09-invalid-metric',[MF,'query','--metrics','invented_profit'],False)
run('10-invalid-dimension',[MF,'query','--metrics','total_revenue','--group-by','shipment__invented'],False)
run('11-explain',[MF,'query','--metrics','margin_rate','--group-by','metric_time__month','--explain'])
after=hashlib.sha256(manifest.read_bytes()).hexdigest()
results.append(dict(test='manifest-unchanged-by-mf',passed=before==after,sha256=after))
run('12-rebuild',[DBT,'build','--profiles-dir','.'])
con=duckdb.connect('probe.duckdb',read_only=True)
assert con.execute('select count(*),sum(revenue) from main.incremental_probe').fetchone()==(4,Decimal('1000.00'))
assert con.execute('select * from main.json_probe').fetchone()==(5,Decimal('125.50'),None)
checks={
 'totals': (None, {None:(1000,600,4,0.4)}),
 'daily':('metric_time__day',{'2026-01-01':(400,240,2,0.4),'2026-01-02':(200,160,1,0.2),'2026-02-01':(400,200,1,0.5)}),
 'monthly':('metric_time__month',{'2026-01-01':(600,400,3,1/3),'2026-02-01':(400,200,1,0.5)}),
 'regions':('shipment__region',{'SE':(400,240,2,0.4),'NE':(600,360,2,0.4)}),
 'filtered':(None,{None:(600,360,2,0.4)})}
for name,(key,expected) in checks.items():
    rows=list(csv.DictReader(open(f'evidence/{name}.csv')))
    assert len(rows)==len(expected),(name,rows)
    for row in rows:
        k=row[key][:10] if key and key.startswith('metric_time') else row[key] if key else None
        actual=[float(row[m]) for m in ['total_revenue','total_cost','shipment_count','margin_rate']]
        assert all(abs(a-b)<1e-8 for a,b in zip(actual,expected[k])),(name,actual,expected[k])
    results.append(dict(test='oracle-'+name,passed=True))
results.append(dict(test='json-and-incremental-idempotency',passed=True))
results.append(dict(test='duckdb-python-version',version=duckdb.__version__,passed=True))
con.close()
seed=ROOT/'seeds/shipments.csv'
original=seed.read_text()
try:
    seed.write_text(original.replace('1,2026-01-01,SE,100,60','1,2026-01-01,SE,150,60'))
    run('13-late-correction',[DBT,'build','--profiles-dir','.'])
    with duckdb.connect('probe.duckdb',read_only=True) as c:
        assert c.execute('select count(*),sum(revenue) from main.incremental_probe').fetchone()==(4,Decimal('1050.00'))
    results.append(dict(test='incremental-correction-oracle',passed=True))
finally:
    seed.write_text(original)
    run('14-restore-fixture',[DBT,'build','--profiles-dir','.'])
run('15-driver-version',[DBT,'show','--profiles-dir','.','--inline','select version() as duckdb_version','--output','json'])
run('16-compile-docs',[DBT,'compile','--profiles-dir','.','--static-analysis','strict','--generate-info-schema'])
run('16-docs',[str(ROOT/'.venv-mf/bin/python'),'pinned_docs.py'],sandbox=False)
(ROOT/'evidence/semantic_manifest.json').write_bytes(manifest.read_bytes())
(ROOT/'evidence/results.json').write_text(json.dumps(results,indent=2)+'\n')
assert all(r['passed'] for r in results)
print('ALL PROBE CHECKS PASSED')
