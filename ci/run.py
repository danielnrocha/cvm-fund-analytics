"""Linux offline CI entrypoint. Baseline is an explicitly selected sealed artifact."""
import argparse,json,os,platform,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.snapshot import build,read_metrics,PYTHON
from release.snapshots import _verify,promote,rollback
from release.uat import evaluate
from ci.artifacts import check_lineage

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--id',required=True)
    p.add_argument('--baseline-root',type=Path);p.add_argument('--baseline-id');p.add_argument('--bootstrap',action='store_true');a=p.parse_args()
    if platform.system()!='Linux' or platform.machine()!='aarch64':p.error('Validated CI platform is Linux aarch64')
    if not a.bootstrap and not (a.baseline_root and a.baseline_id):p.error('Select a sealed baseline; bootstrap is explicit')
    if a.bootstrap and (a.baseline_root or a.baseline_id):p.error('Bootstrap and baseline are mutually exclusive')
    if sys.flags.optimize:p.error('Optimized validators are forbidden')
    os.environ.pop('PYTHONOPTIMIZE',None)
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=True);root=out/'releases'
    (ROOT/'transform/evidence').mkdir(exist_ok=True)
    def run(name,args):
        with (out/(name+'.log')).open('w') as f:subprocess.run(args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=900)
    for group in ['business','ingestion','release','ci']:
        run('tests-'+group,[str(PYTHON),'-m','unittest','discover','-s','tests/'+group,'-v'])
    # Full native build is never replaced by a state-based subset.
    candidate=build(root,'dev',a.id)
    lineage=check_lineage(candidate/'project/target/info_schema/v1/dbt.column_lineage.parquet')
    run('docs',[str(PYTHON),str(ROOT/'ci/docs.py'),'--project',str(root/'work/dev'/a.id/'project')])
    baseline=a.id if a.bootstrap else a.baseline_id
    if not a.bootstrap:
        if baseline==a.id:p.error('Candidate id must differ from baseline')
        source=_verify(a.baseline_root,baseline)
        shutil.copytree(source,root/'snapshots'/baseline)
        _verify(root,baseline)
    initial=evaluate(root,baseline,baseline,bootstrap=True)
    promote(root,'uat',baseline,gate=initial)
    gate=initial if a.bootstrap else evaluate(root,baseline,a.id)
    if not a.bootstrap:promote(root,'uat',a.id,baseline,gate=gate)
    if not a.bootstrap:
        rollback(root,'uat',a.id)
        promote(root,'uat',a.id,baseline,gate=gate)
    run('semantic-mutation',[str(PYTHON),str(ROOT/'tests/ci/check_semantic_gate.py'),'--root',str(root),'--baseline',a.id,'--output',str(out/'semantic-mutation.json')])
    run('history',[str(PYTHON),str(ROOT/'scripts/check_history.py')])
    run('rejections',[str(PYTHON),str(ROOT/'scripts/check_rejections.py')])
    shutil.copytree(ROOT/'transform/evidence',out/'integration-evidence')
    result={'passed':True,'platform':platform.platform(),'candidate':a.id,'required_lineage_edges':lineage,'baseline':baseline,'bootstrap':a.bootstrap,'gate':str(gate),'metrics':read_metrics(root,'uat')}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
