"""Remove PL non-additivity in a disposable project; oracle must reject result."""
from pathlib import Path
from decimal import Decimal
import csv,os,shutil,subprocess,tempfile,yaml,json
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'transform/evidence'
with tempfile.TemporaryDirectory(prefix='cvm-semantic-mutation-') as tmp:
    p=Path(tmp)/'transform';shutil.copytree(ROOT/'transform',p,ignore=shutil.ignore_patterns('target','logs','evidence','*.duckdb*'))
    shutil.copy(ROOT/'transform/cvm_demo.duckdb',p/'mutated.duckdb')
    config=p/'models/semantic.yml';d=yaml.safe_load(config.read_text())
    d['models'][0]['metrics'][0].pop('non_additive_dimension');config.write_text(yaml.safe_dump(d,sort_keys=False))
    env={**os.environ,'DBT_PROFILES_DIR':str(p),'CVM_DB_PATH':str(p/'mutated.duckdb'),'DBT_SEND_ANONYMOUS_USAGE_STATS':'false'}
    for name,cmd in [('parse',[str(ROOT/'compatibility/dbt-v2-metricflow/.venv-dbt/bin/dbt'),'parse','--profiles-dir',str(p)]),('query',[str(ROOT/'compatibility/dbt-v2-metricflow/.venv-mf/bin/mf'),'query','--metrics','reported_net_assets_eop','--csv',str(p/'result.csv')])]:
        run=subprocess.run(cmd,cwd=p,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (E/f'mutation-semantic-{name}.log').write_text(run.stdout);assert run.returncode==0,run.stdout
    actual=Decimal(next(csv.DictReader((p/'result.csv').open()))['reported_net_assets_eop'])
    assert actual!=Decimal('119385193058.06'),actual
    (E/'semantic-mutation.json').write_text(json.dumps({'wrong_pl':str(actual),'expected_pl':'119385193058.06','detected':True},indent=2)+'\n')
print('Removing non-additivity detected by real PL oracle')
