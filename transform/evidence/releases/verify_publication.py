import sys,json,os,shutil,tempfile,subprocess,hashlib
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
import duckdb,yaml
from release.snapshots import promote,rollback,resolve
from scripts.snapshot import read_metrics,DEFAULT,ROOT,PYTHON
root=DEFAULT;a='cvm-ingestion-v1';b='cvm-atomic-v2'
checks={}
for env in ['dev','uat']:promote(root,env,a)
pinned=resolve(root,'dev')
with duckdb.connect(str(pinned/'snapshot.duckdb'),read_only=True) as c:
    old=c.execute('select count(*) from fct_daily').fetchone()
    promote(root,'dev',b,a)
    assert resolve(root,'uat').name==a
    assert c.execute('select count(*) from fct_daily').fetchone()==old==(7560,)
checks['pinned_reader_and_environment_isolation']=True
promote(root,'uat',b,a)
try:promote(root,'uat',a,a)
except ValueError:checks['stale_cas_rejected']=True
else:raise AssertionError('CAS accepted')
rollback(root,'uat',b)
assert resolve(root,'uat')==root/'snapshots'/a
checks['rollback_exact_bundle']=read_metrics(root,'uat')
promote(root,'uat',b,a)
bundle=resolve(root,'uat');db=bundle/'snapshot.duckdb'
digest=lambda:hashlib.sha256(db.read_bytes()).hexdigest()
before=digest()
with duckdb.connect(str(db),read_only=False,config={'access_mode':'READ_ONLY'}) as c:
    try:c.execute('create table forbidden_write(i int)')
    except duckdb.InvalidInputException:checks['readonly_enforced']=True
    else:raise AssertionError('write accepted')
with tempfile.TemporaryDirectory() as td:
    project=Path(td)/'project'
    shutil.copytree(bundle/'project',project,ignore=shutil.ignore_patterns('logs','evidence'))
    for p in project.rglob('*'):
        if p.is_file():p.chmod(0o644)
    (project/'evidence').mkdir()
    profile=yaml.safe_load((project/'profiles.yml').read_text())
    for out in profile['cvm_demo']['outputs'].values():
        out['path']=str(db);out['config_options']={'access_mode':'READ_ONLY'}
    (project/'profiles.yml').write_text(yaml.safe_dump(profile))
    env={**os.environ,'CVM_PROJECT_DIR':str(project),'CVM_TARGET':'uat','CVM_DB_PATH':str(db),'CVM_UAT_DB_PATH':str(db)}
    env.pop('PYTHONOPTIMIZE',None)
    r=subprocess.run([str(PYTHON),str(ROOT/'scripts/check_semantics.py')],env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (ROOT/'transform/evidence/releases/09-published-metricflow.log').write_text(r.stdout)
    assert r.returncode==0,r.stdout
    checks['published_metricflow']=json.loads((project/'evidence/semantic-results.json').read_text())
assert digest()==before
checks['database_unchanged_sha256']=before
checks['final']={env:read_metrics(root,env) for env in ['dev','uat']}
(ROOT/'transform/evidence/releases/publication-results.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
