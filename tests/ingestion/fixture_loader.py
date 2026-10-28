"""Test-only adapter: old synthetic CSV fixtures → source tables, never dbt seeds."""
import csv,json,pathlib,sys,collections
import duckdb
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from ingestion.store import DDL
FIELDS={'kind':'TP_FUNDO_CLASSE','cnpj':'CNPJ_FUNDO_CLASSE','subclass':'ID_SUBCLASSE','report_date':'DT_COMPTC','pl':'VL_PATRIM_LIQ','subscriptions':'CAPTC_DIA','redemptions':'RESG_DIA','quota':'VL_QUOTA','total_assets':'VL_TOTAL','investors':'NR_COTST'}
def load(project,db):
 def read(name):return list(csv.DictReader((project/'seeds'/name).open()))
 with duckdb.connect(str(db),config={'storage_compatibility_version':'v1.4.0'}) as c:
  c.execute('begin');c.execute('drop schema if exists landing cascade');c.execute(DDL)
  for r in read('entities.csv'):c.execute('insert into landing.registry_cohort values (?,?,?)',[r['cnpj'],r['entity_id'],r['classification_at_capture']])
  for r in read('report_calendar.csv'):c.execute('insert into landing.report_calendar values (?)',[r['report_date']])
  for r in read('captures.csv'):c.execute('insert into landing.captures values (?,?)',[r['capture_id'],r['captured_at']+'+00:00'])
  counts=collections.Counter()
  for r in read('observations.csv'):
   payload=json.dumps({'schema_version':1,'error':None,'data':{v:r[k] or None for k,v in FIELDS.items()}})
   c.execute('insert into landing.raw_envelopes values (?,?,?,?)',[r['capture_id'],r['source_id'],r['report_date'][:7].replace('-',''),payload]);counts[(r['capture_id'],r['source_id'].split(':')[0])]+=1
  for (capture,file_sha),n in counts.items():c.execute('insert into landing.files values (?,?,?,?,?)',[capture,file_sha,'fixture.csv',n,0])
  c.execute('commit')
