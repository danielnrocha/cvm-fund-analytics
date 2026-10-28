"""Adversarial integration: simulate a faulty attestation; live MF gate must still block it."""
import argparse,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import yaml
from release.snapshots import _verify,seal,promote,resolve
from release.uat import evaluate
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--baseline',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 baseline=_verify(a.root,a.baseline)
 with tempfile.TemporaryDirectory(prefix='cvm-negative-uat-') as td:
  root=Path(td);snapshots=root/'snapshots';snapshots.mkdir();shutil.copytree(baseline,snapshots/a.baseline)
  work=root/'mutation';shutil.copytree(baseline,work)
  for f in work.rglob('*'):
   if f.is_file():f.chmod(0o644)
  (work/'bundle.json').unlink()
  config=work/'project/models/semantic.yml';data=yaml.safe_load(config.read_text());data['models'][0]['metrics'][0].pop('non_additive_dimension');config.write_text(yaml.safe_dump(data,sort_keys=False))
  env={**os.environ,'CVM_TARGET':'dev','CVM_DB_PATH':str(work/'snapshot.duckdb'),'DBT_PROFILES_DIR':str(work/'project'),'DBT_SEND_ANONYMOUS_USAGE_STATS':'false'}
  r=subprocess.run([str(ROOT/'compatibility/dbt-v2-metricflow/.venv-dbt/bin/dbt'),'parse','--profiles-dir',str(work/'project')],cwd=work/'project',env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
  if r.returncode:raise RuntimeError(r.stdout)
  # Deliberate faulty-builder fixture: retain passed attestation to exercise this separate gate.
  seal(root,work,'bad-semiadditivity')
  initial=evaluate(root,a.baseline,a.baseline,bootstrap=True);promote(root,'uat',a.baseline,gate=initial)
  pointer=root/'environments/uat/current.json';before=pointer.read_bytes()
  report=evaluate(root,a.baseline,'bad-semiadditivity');result=json.loads(report.read_text())
  if result['passed'] or not result['differences']:raise AssertionError('Semantic mutation escaped comparison')
  try:promote(root,'uat','bad-semiadditivity',a.baseline,gate=report)
  except ValueError:pass
  else:raise AssertionError('UAT accepted regression')
  if pointer.read_bytes()!=before or resolve(root,'uat').name!=a.baseline:raise AssertionError('Failed gate changed UAT')
  a.output.write_text(json.dumps({'blocked':True,'pointer_unchanged':True,'changed_probes':{k:len(v) for k,v in result['differences'].items()}},indent=2)+'\n')
  print(a.output.read_text())
if __name__=='__main__':main()
