"""Native dbt unit/contract mutation tests, semantic oracles and a pinned docs driver."""
from pathlib import Path
import os, subprocess, json, csv, tempfile
from decimal import Decimal
import duckdb
P=Path(__file__).resolve().parent;os.chdir(P)
env=os.environ.copy();env.update(DBT_PROFILES_DIR=str(P),DBT_SEND_ANONYMOUS_USAGE_STATS='false')
DBT=str(P/'.venv-dbt/bin/dbt');MF=str(P/'.venv-mf/bin/mf');PY=str(P/'.venv-mf/bin/python')
prefix=['/usr/bin/sandbox-exec','-f','network-deny.sb'];results=[]
def run(name,cmd,expected=0,contains=None,sandbox=True):
 p=subprocess.run((prefix if sandbox else [])+cmd,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
 Path('evidence/'+name+'.log').write_text(p.stdout)
 passed=(p.returncode==0 if expected==0 else p.returncode!=0) and (contains is None or contains.lower() in p.stdout.lower())
 results.append({'test':name,'passed':passed,'exit_code':p.returncode})
 Path('evidence/remaining-gates-results.json').write_text(json.dumps(results,indent=2)+'\n')
 print(name,p.returncode,'PASS' if passed else 'FAIL',flush=True)
 assert passed,p.stdout
 return p
run('36-unit-green',[DBT,'test','--select','test_type:unit','--profiles-dir','.'],contains='Passed unit_test')
f=Path('models/stg_external_json.sql');original=f.read_text()
try:
 f.write_text(original.replace("then 'invalid_revenue'", "then 'wrong_reason'"))
 run('37-unit-red',[DBT,'test','--select','test_type:unit','--profiles-dir','.'],expected=1,contains='classifies_invalid_json_and_revenue')
 # Require an actual row mismatch, not a parser/setup failure.
 log=Path('evidence/37-unit-red.log').read_text()
 assert 'wrong_reason' in log and 'invalid_revenue' in log,log
finally:f.write_text(original)
run('38-unit-green-restored',[DBT,'test','--select','test_type:unit','--profiles-dir','.'],contains='Passed unit_test')
run('39-contract-green',[DBT,'build','--select','contract_probe','--profiles-dir','.','--static-analysis','strict'])
f=Path('models/contract_probe.sql');original=f.read_text()
for name,mutated in [('type',original.replace('as decimal(18,2)', 'as varchar')),('missing',original.replace('as profit','as renamed_profit'))]:
 try:
  f.write_text(mutated)
  run('40-contract-red-'+name,[DBT,'build','--select','contract_probe','--profiles-dir','.','--static-analysis','strict'],expected=1,contains='contract')
 finally:f.write_text(original)
run('41-contract-restored',[DBT,'build','--select','contract_probe','--profiles-dir','.','--static-analysis','strict'])
run('42-semantic-validate',[MF,'validate-configs'])
metrics='balance_last_observed_date,balance_latest_per_account'
cases=[('monthly',['--group-by','metric_time__month']),('total',[]),('daily',['--group-by','metric_time__day']),('jan',['--start-time','2026-01-01','--end-time','2026-01-31']),('account',['--group-by','account,metric_time__month']),('no-observation',['--start-time','2026-01-15','--end-time','2026-01-15'])]
for name,extra in cases:run('43-balance-'+name,[MF,'query','--metrics',metrics,*extra,'--csv','evidence/balance-'+name+'.csv'])
def rows(name):return list(csv.DictReader(open('evidence/balance-'+name+'.csv')))
def values(row):return tuple((Decimal(row[k]) if row[k] else None) for k in metrics.split(','))
assert {r['metric_time__month'][:10]:values(r) for r in rows('monthly')}=={'2026-01-01':(Decimal(110),Decimal(330)),'2026-02-01':(Decimal(390),Decimal(390))}
assert values(rows('total')[0])==(Decimal(390),Decimal(390))
assert values(rows('jan')[0])==(Decimal(110),Decimal(330))
expected={'2026-01-01':300,'2026-01-30':220,'2026-01-31':110,'2026-02-01':360,'2026-02-28':390}
assert {r['metric_time__day'][:10]:values(r) for r in rows('daily')}=={k:(Decimal(v),Decimal(v)) for k,v in expected.items()}
assert not rows('no-observation') or all(values(r)==(None,None) for r in rows('no-observation'))
assert len(rows('account'))==4
assert { (r['account'],r['metric_time__month'][:10]):values(r) for r in rows('account')}=={('A','2026-01-01'):(Decimal(110),Decimal(110)),('B','2026-01-01'):(None,Decimal(220)),('A','2026-02-01'):(Decimal(130),Decimal(130)),('B','2026-02-01'):(Decimal(260),Decimal(260))}
with duckdb.connect('probe.duckdb',read_only=True) as c:
 assert c.execute('select sum(balance) from balance_probe').fetchone()[0]==Decimal(1380)
 assert c.execute('select count(*) from (select account_id,balance_date,count(*) n from balance_probe group by 1,2 having n>1)').fetchone()[0]==0
results.append({'test':'semiadditive-oracles-and-grain','passed':True,'naive_sum':1380,'correct_total':390,'january_common_observed':110,'january_latest_per_account':330})
# Mutate semantics, not data: removing nonadditivity must expose the wrong total.
f=Path('models/balance_probe.yml');original=f.read_text()
try:
 import yaml
 y=yaml.safe_load(original)
 for m in y['models'][0]['metrics']:m.pop('non_additive_dimension')
 f.write_text(yaml.safe_dump(y,sort_keys=False))
 run('44-mutated-semantic-parse',[DBT,'parse','--profiles-dir','.'])
 run('45-mutated-query',[MF,'query','--metrics',metrics,'--csv','evidence/balance-mutated.csv'])
 assert values(rows('mutated')[0])==(Decimal(1380),Decimal(1380))
 results.append({'test':'semantic-mutation-detected-by-oracle','passed':True})
finally:f.write_text(original)
run('46-final-build',[DBT,'build','--profiles-dir','.','--static-analysis','strict','--generate-info-schema'])
run('47-restored-balance',[MF,'query','--metrics',metrics,'--csv','evidence/balance-restored.csv'])
assert values(rows('restored')[0])==(Decimal(390),Decimal(390))
run('48-driver-verify',[PY,'pinned_docs.py','--verify-only'])
with tempfile.TemporaryDirectory(dir=P) as td:
 lock=json.loads(Path('docs-driver.lock.json').read_text());Path(td,lock['filename']).write_bytes(b'corrupt driver fixture')
 run('49-corrupt-driver-rejected',[PY,'pinned_docs.py','--driver-dir',td,'--verify-only'],expected=1,contains='SHA-256/size mismatch')
run('50-pinned-docs',[PY,'pinned_docs.py'],sandbox=False)
Path('evidence/remaining-gates-results.json').write_text(json.dumps(results,indent=2)+'\n')
print('ALL REMAINING GATES PASSED',flush=True)
