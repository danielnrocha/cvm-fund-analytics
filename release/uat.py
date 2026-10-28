"""Exact semantic regression gate. Local filesystem owner and validator runtime are trusted."""
import csv,hashlib,io,json,os,shutil,subprocess,tempfile
from decimal import Decimal,InvalidOperation
from pathlib import Path
import yaml
from release.snapshots import _verify
ROOT=Path(__file__).resolve().parents[1]
INPUTS=('profiling/cvm/evidence/sources.json','profiling/cvm/evidence/cohort.csv','profiling/cvm/evidence/calendar.json','profiling/cvm/evidence/monthly-oracles.json')
METRICS='reported_net_assets_eop,net_flow,reporting_observations,expected_observations,reporting_entities_eop,expected_entities_eop'
QUERIES={
 'total':{'keys':[],'args':[],'metrics':METRICS},
 'monthly':{'keys':['metric_time__month'],'args':['--group-by','metric_time__month'],'metrics':METRICS},
 'daily_entity':{'keys':['metric_time__day','reporting_entity'],'args':['--group-by','metric_time__day,reporting_entity'],'metrics':METRICS},
 'coverage':{'keys':['metric_time__month'],'args':['--group-by','metric_time__month'],'metrics':'reporting_coverage_period,reporting_coverage_eop'},
}
def compare_csv(a,b,keys):
    def parse(text):
        reader=csv.DictReader(io.StringIO(text));columns=reader.fieldnames
        if not columns or len(set(columns))!=len(columns) or not set(keys)<=set(columns):raise ValueError('Invalid columns')
        rows={}
        for row in reader:
            if None in row or any(v is None for v in row.values()):raise ValueError('Malformed row')
            key=tuple(row[k] for k in keys)
            if any(not k for k in key) or key in rows:raise ValueError('Empty or duplicate group')
            values={}
            for k,v in row.items():
                if k in keys:continue
                if v=='':values[k]=None;continue
                try:d=Decimal(v)
                except InvalidOperation as exc:raise ValueError('Non-numeric metric') from exc
                if not d.is_finite():raise ValueError('Non-finite metric')
                values[k]=d
            if not values:raise ValueError('No metrics')
            rows[key]=values
        if not rows:raise ValueError('Empty result')
        return set(columns),rows
    ac,ar=parse(a);bc,br=parse(b)
    if ac!=bc:return [{'kind':'columns','baseline':sorted(ac),'candidate':sorted(bc)}]
    differences=[]
    for key in sorted(ar.keys()|br.keys()):
        if key not in ar or key not in br:differences.append({'group':key,'kind':'missing_group'});continue
        for metric in sorted(ar[key]):
            if ar[key][metric]!=br[key][metric]:differences.append({'group':key,'metric':metric,'baseline':str(ar[key][metric]),'candidate':str(br[key][metric])})
    return differences

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def binding(bundle):return digest(bundle/'bundle.json')
def inputs(bundle):
    hashes=json.loads((bundle/'validation.json').read_text()).get('source_hashes',{})
    if any(not hashes.get(k) for k in INPUTS):raise ValueError('Missing frozen input fingerprints')
    return {k:hashes[k] for k in INPUTS}
def collect(bundle):
    """Run MetricFlow against an immutable DB, writing only in a disposable project."""
    mf=ROOT/'compatibility/dbt-v2-metricflow/.venv-mf/bin/mf'
    with tempfile.TemporaryDirectory(prefix='cvm-uat-') as tmp:
        project=Path(tmp)/'project'
        shutil.copytree(bundle/'project',project,ignore=shutil.ignore_patterns('logs','evidence'))
        for p in project.rglob('*'):
            if p.is_file():p.chmod(0o644)
        profile=yaml.safe_load((project/'profiles.yml').read_text())
        profile['cvm_demo']['target']='uat'
        for out in profile['cvm_demo']['outputs'].values():
            out['path']=str((bundle/'snapshot.duckdb').resolve());out['config_options']={'access_mode':'READ_ONLY'}
        (project/'profiles.yml').write_text(yaml.safe_dump(profile))
        env={**os.environ,'DBT_PROFILES_DIR':str(project),'CVM_TARGET':'uat','DBT_SEND_ANONYMOUS_USAGE_STATS':'false'}
        results={}
        for name,spec in QUERIES.items():
            output=Path(tmp)/(name+'.csv')
            run=subprocess.run([str(mf),'query','--metrics',spec['metrics'],*spec['args'],'--csv',str(output)],cwd=project,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
            if run.returncode:raise ValueError('MetricFlow query failed: '+name+'\n'+run.stdout)
            results[name]=output.read_text()
        return results

def differences(left,right):
    if set(left)!=set(QUERIES) or set(right)!=set(QUERIES):raise ValueError('Incomplete query suite')
    for results in (left,right):
        for name,spec in QUERIES.items():
            header=next(csv.reader(io.StringIO(results[name])),[])
            if set(header)!=set(spec['keys'])|set(spec['metrics'].split(',')):raise ValueError('Unexpected semantic result schema')
    return {name:diff for name,spec in QUERIES.items() if (diff:=compare_csv(left[name],right[name],spec['keys']))}

def evaluate(root,baseline,candidate,bootstrap=False):
    root=Path(root).resolve();a=_verify(root,baseline);b=_verify(root,candidate)
    if bootstrap and baseline!=candidate:raise ValueError('Bootstrap must explicitly self-compare validated candidate')
    if inputs(a)!=inputs(b):raise ValueError('Baseline and candidate inputs differ')
    report={'version':1,'suite':QUERIES,'baseline':baseline,'candidate':candidate,'expected':None if bootstrap else baseline,
            'baseline_hash':binding(a),'candidate_hash':binding(b),'inputs':inputs(a),
            'baseline_results':collect(a),'candidate_results':collect(b)}
    report['differences']=differences(report['baseline_results'],report['candidate_results'])
    report['passed']=not report['differences']
    # Detect drift throughout query execution, before attesting.
    _verify(root,baseline);_verify(root,candidate)
    folder=root/'gates';folder.mkdir(parents=True,exist_ok=True)
    fd,path=tempfile.mkstemp(prefix=f'{baseline}--{candidate}-',suffix='.json',dir=folder)
    with os.fdopen(fd,'w') as f:json.dump(report,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    return Path(path)

def verify_gate(root,gate,expected,candidate):
    if gate is None:raise ValueError('UAT requires semantic gate report')
    report=json.loads(Path(gate).read_text())
    baseline=candidate if expected is None else expected
    if report.get('version')!=1 or report.get('suite')!=QUERIES:raise ValueError('Unknown gate suite')
    if (report.get('baseline'),report.get('candidate'),report.get('expected'))!=(baseline,candidate,expected):raise ValueError('Gate bound to different release pair')
    a=_verify(root,baseline);b=_verify(root,candidate)
    if (report.get('baseline_hash'),report.get('candidate_hash'))!=(binding(a),binding(b)):raise ValueError('Gate bundle identity changed')
    if report.get('inputs')!=inputs(a) or inputs(a)!=inputs(b):raise ValueError('Gate input identity changed')
    if report.get('passed') is not True or report.get('differences')!={} or differences(report['baseline_results'],report['candidate_results']):raise ValueError('Semantic regression blocks UAT promotion')
    return digest(Path(gate))
