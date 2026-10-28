"""Build validated local snapshots and atomically promote independent environment pointers."""
from pathlib import Path
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from release.snapshots import seal,promote,rollback,resolve,_name,_environment
import duckdb
ROOT=Path(__file__).resolve().parents[1];DEFAULT=ROOT/'data/releases'
PYTHON=ROOT/'compatibility/dbt-v2-metricflow/.venv-mf/bin/python'
DBT=ROOT/'compatibility/dbt-v2-metricflow/.venv-dbt/bin/dbt';MF=ROOT/'compatibility/dbt-v2-metricflow/.venv-mf/bin/mf'
def source_hashes():
    paths=[]
    for folder in ['transform','ingestion','release','scripts','ci','.github/workflows']:
        for p in (ROOT/folder).rglob('*'):
            relative=p.relative_to(ROOT/folder)
            if any(part in ('target','logs','evidence','__pycache__','seeds') for part in relative.parts):continue
            if p.is_file() and (p.suffix in ('.py','.sql','.yml','.yaml','.toml','.lock','.json') or p.name=='Dockerfile'):
                paths.append(p)
    if (ROOT/'.dockerignore').is_file():paths.append(ROOT/'.dockerignore')
    paths.extend(ROOT.glob('compatibility/dbt-v2-metricflow/requirements-*.lock'))
    paths.extend(p for p in ROOT.glob('profiling/cvm/evidence/*') if p.is_file() and p.suffix!='.log')
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}

def build(root,environment,release_id):
    _name(release_id);_environment(environment);root=Path(root).resolve()
    work=root/'work'/environment/release_id;work.mkdir(parents=True,exist_ok=False)
    before=source_hashes()
    project=work/'project'
    shutil.copytree(ROOT/'transform',project,ignore=shutil.ignore_patterns('target','logs','evidence','*.duckdb*','seeds'))
    (project/'evidence').mkdir();db=work/'snapshot.duckdb'
    env={**os.environ,'CVM_TARGET':environment,'CVM_DB_PATH':str(db),'CVM_UAT_DB_PATH':str(db),'CVM_PROJECT_DIR':str(project),'DBT_PROFILES_DIR':str(project),'DBT_SEND_ANONYMOUS_USAGE_STATS':'false'}
    env.pop('PYTHONOPTIMIZE',None)
    if before!=source_hashes():raise ValueError('Source changed during copy')
    for relative,digest in before.items():
        if relative.startswith('transform/'):
            copied=project/relative.removeprefix('transform/')
            if not copied.is_file() or hashlib.sha256(copied.read_bytes()).hexdigest()!=digest:raise ValueError('Copied project differs from source fingerprint')
    def run(name,args):
        result=subprocess.run(args,cwd=project,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
        (work/f'{name}.log').write_text(result.stdout)
        if result.returncode:raise RuntimeError(f'{name} failed; see {work/name}.log')
    run('ingest',[str(PYTHON),str(ROOT/'scripts/ingest_cvm.py')])
    run('build',[str(DBT),'build','--profiles-dir',str(project),'--target',environment,'--static-analysis','strict','--generate-info-schema'])
    run('oracles',[str(PYTHON),str(ROOT/'scripts/check_real_oracles.py')])
    run('validate',[str(MF),'validate-configs'])
    run('semantic',[str(PYTHON),str(ROOT/'scripts/check_semantics.py')])
    results=json.loads((project/'target/run_results.json').read_text())
    manifest=json.loads((project/'target/manifest.json').read_text())
    if not results['results'] or any(r['status'] not in ('success','pass') for r in results['results']):raise ValueError('Incomplete build')
    if results['metadata']['invocation_id']!=manifest['metadata']['invocation_id']:raise ValueError('Artifacts from different builds')
    if before!=source_hashes():raise ValueError('Source changed during validation')
    # No child process remains. Flush WAL, close connection, then seal on the same host.
    with duckdb.connect(str(db)) as c:c.execute('checkpoint')
    if Path(str(db)+'.wal').exists():raise ValueError('Database still has WAL')
    (work/'validation.json').write_text(json.dumps({'passed':True,'environment':environment,'invocation_id':results['metadata']['invocation_id'],'resources':len(results['results']),'checks':['native_build','real_oracles','metricflow_validate','metricflow_queries'],'source_hashes':before},indent=2)+'\n')
    return seal(root,work,release_id)
def read_metrics(root,environment):
    bundle=resolve(root,environment)
    # Pin once; promotions cannot redirect this connection.
    with duckdb.connect(str(bundle/'snapshot.duckdb'),read_only=True) as c:
        result=c.execute('''select sum(pl) filter(where report_date=date '2026-09-30'),sum(net_flow),sum(reported),sum(expected) from fct_daily''').fetchone()
    return {'release_id':bundle.name,'pl':str(result[0]),'flow':str(result[1]),'reported':result[2],'expected':result[3]}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['build','compare','promote','rollback','read']);parser.add_argument('--environment',choices=['dev','uat'],required=True);parser.add_argument('--id');parser.add_argument('--expected');parser.add_argument('--baseline');parser.add_argument('--bootstrap',action='store_true');parser.add_argument('--gate',type=Path);parser.add_argument('--root',type=Path,default=DEFAULT);a=parser.parse_args()
    if a.action in ('build','compare','promote') and not a.id:parser.error('--id is required')
    if a.action=='compare':
        from release.uat import evaluate
        if not a.baseline:parser.error('--baseline is required')
        report=evaluate(a.root,a.baseline,a.id,bootstrap=a.bootstrap);print(report)
        if not json.loads(report.read_text())['passed']:raise SystemExit(1)
    elif a.action=='build':print(build(a.root,a.environment,a.id))
    elif a.action=='promote':promote(a.root,a.environment,a.id,a.expected,gate=a.gate);print(json.dumps(read_metrics(a.root,a.environment)))
    elif a.action=='rollback':rollback(a.root,a.environment,a.expected);print(json.dumps(read_metrics(a.root,a.environment)))
    else:print(json.dumps(read_metrics(a.root,a.environment)))
if __name__=='__main__':main()
