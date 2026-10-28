"""MetricFlow queries against frozen real oracles; no SQL computed expectations."""
from pathlib import Path
from decimal import Decimal as D
import csv,json,os,subprocess
ROOT=Path(__file__).resolve().parents[1];P=Path(os.environ.get('CVM_PROJECT_DIR',str(ROOT/'transform')));E=P/'evidence'
MF=ROOT/'compatibility/dbt-v2-metricflow/.venv-mf/bin/mf'
env={**os.environ,'DBT_PROFILES_DIR':str(P),'DBT_SEND_ANONYMOUS_USAGE_STATS':'false'}
metrics='reported_net_assets_eop,net_flow,reporting_observations,expected_observations,reporting_entities_eop,expected_entities_eop'
def query(name,extra,requested=metrics):
    run=subprocess.run([str(MF),'query','--metrics',requested,*extra,'--csv',str(E/f'{name}.csv')],cwd=P,env=env,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    (E/f'{name}.log').write_text(run.stdout);assert run.returncode==0,run.stdout
    return list(csv.DictReader((E/f'{name}.csv').open()))
oracles=json.loads((ROOT/'profiling/cvm/evidence/monthly-oracles.json').read_text())
monthly=query('semantic-monthly',['--group-by','metric_time__month'])
assert len(monthly)==6
for r in monthly:
    expected=next(x for x in oracles if x['period']==r['metric_time__month'][:7])
    for key in ['reported_net_assets_eop','net_flow']:
        assert D(r[key])==D(expected[key]),(key,r)
    assert int(r['reporting_observations'])==expected['observations']
    assert int(r['reporting_entities_eop'])==60 and int(r['expected_entities_eop'])==60
    assert int(r['expected_observations'])=={'2026-04':1200,'2026-05':1200,'2026-06':1260,'2026-07':1380,'2026-08':1260,'2026-09':1260}[expected['period']]
total=query('semantic-total',[])[0]
assert D(total['reported_net_assets_eop'])==D('119385193058.06')
assert D(total['net_flow'])==D('4725910556.15')
assert int(total['reporting_observations'])==7554 and int(total['expected_observations'])==7560
# Real gap: this class has no observation on 28 August. Filtering must not retreat.
cohort=list(csv.DictReader((ROOT/'profiling/cvm/evidence/cohort.csv').open()))
entity='CVM:CLASS:'+next(r['ID_Registro_Classe'] for r in cohort if r['cnpj']=='31963249000126')
gap=query('semantic-real-gap',['--start-time','2026-08-28','--end-time','2026-08-28','--where',f"{{{{ Entity('reporting_entity') }}}} = '{entity}'"])
assert len(gap)==1 and gap[0]['reported_net_assets_eop']=='' and gap[0]['net_flow']==''
assert int(gap[0]['reporting_entities_eop'])==0 and int(gap[0]['expected_entities_eop'])==1
coverage=query('semantic-coverage',['--group-by','metric_time__month'],'reporting_coverage_period,reporting_coverage_eop')
assert len(coverage)==6
for r in coverage:
    assert D(r['reporting_coverage_eop'])==1
    if r['metric_time__month'].startswith('2026-04'):
        assert abs(D(r['reporting_coverage_period'])-D(1196)/D(1200))<D('0.000000000001')
(E/'semantic-results.json').write_text(json.dumps({'monthly_oracles':6,'total_stock_not_sum':True,'flow_total':True,'filtered_gap_no_backfill':True,'coverage':True},indent=2)+'\n')
print('MetricFlow real monthly, total, filtered gap and coverage PASS')
