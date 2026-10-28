"""Frozen research cohort; independent Decimal reconciliation, no dbt models."""
import csv, decimal, json, pathlib
import duckdb
P=pathlib.Path(__file__).resolve().parent
c=duckdb.connect(str(P/'profile.duckdb'))
def rows(sql):
 r=c.execute(sql); return [dict(zip([d[0] for d in r.description],x)) for x in r.fetchall()]
# Fail-closed identity: no arbitrary DISTINCT or latest-row resolution.
c.execute('''create or replace table eligible as
with good_class as (select * from classe qualify count(*) over(partition by CNPJ_Classe)=1 and count(*) over(partition by ID_Registro_Classe)=1),
good_fund as (select * from fundo qualify count(*) over(partition by ID_Registro_Fundo)=1),
single_class as (select ID_Registro_Fundo from classe group by 1 having count(*)=1),
good_daily as (select cnpj from daily group by 1 having count(*)=count(distinct DT_COMPTC) and count(distinct substr(DT_COMPTC,1,7))=6 and count(*) filter(where ID_SUBCLASSE is not null)=0 and count(distinct TP_FUNDO_CLASSE)=1 and min(TP_FUNDO_CLASSE)='CLASSES - FIF')
select cl.CNPJ_Classe cnpj,cl.ID_Registro_Classe,cl.ID_Registro_Fundo,cl.Classificacao,cl.Denominacao_Social
from good_class cl join good_fund f using(ID_Registro_Fundo) join single_class sc using(ID_Registro_Fundo) join good_daily d on d.cnpj=cl.CNPJ_Classe
where not exists(select 1 from subclasse s where s.ID_Registro_Classe=cl.ID_Registro_Classe)
and cl.Classificacao in ('Renda Fixa','Multimercado','Ações')''')
c.execute('''create or replace table cohort as select * from eligible qualify row_number() over(partition by Classificacao order by sha256(cnpj),cnpj)<=20''')
cohort=rows('select * from cohort order by Classificacao,cnpj')
assert len(cohort)==60
with (P/'evidence/cohort.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=list(cohort[0]));w.writeheader();w.writerows(cohort)
# First/last day per month are observed global dates, not exchange-calendar claims.
oracles=rows('''with dates as (select substr(DT_COMPTC,1,7) period,max(DT_COMPTC) cutoff from daily group by 1)
select dates.period,dates.cutoff,count(*) observations,count(distinct d.cnpj) entities,
count(*) filter(where DT_COMPTC=cutoff) reporting_at_cutoff,
sum(cast(VL_PATRIM_LIQ as decimal(17,2))) filter(where DT_COMPTC=cutoff) reported_net_assets_eop,
sum(cast(CAPTC_DIA as decimal(17,2))-cast(RESG_DIA as decimal(17,2))) net_flow,
sum(cast(NR_COTST as bigint)) filter(where DT_COMPTC=cutoff) reported_investor_accounts_eop
from daily d join cohort h using(cnpj) join dates on substr(d.DT_COMPTC,1,7)=dates.period group by 1,2 order by 1''')
keys={r['cnpj'] for r in cohort}; independent={}
D=decimal.Decimal
for p in sorted((P/'extracted').glob('inf*/*.csv')):
 if '.utf8.' in p.name: continue
 with p.open(encoding='latin1',newline='') as f:
  for r in csv.DictReader(f,delimiter=';'):
   key=''.join(ch for ch in r['CNPJ_FUNDO_CLASSE'] if ch.isdigit())
   if key not in keys:continue
   period=r['DT_COMPTC'][:7]; v=independent.setdefault(period,{'net_flow':D(0),'by_date':{},'observations':0})
   v['net_flow']+=D(r['CAPTC_DIA'])-D(r['RESG_DIA']);v['observations']+=1
   day=v['by_date'].setdefault(r['DT_COMPTC'],[D(0),0,0]);day[0]+=D(r['VL_PATRIM_LIQ']);day[1]+=int(r['NR_COTST']);day[2]+=1
for r in oracles:
 v=independent[r['period']];day=v['by_date'][r['cutoff']]
 assert v['net_flow']==r['net_flow'] and v['observations']==r['observations']
 assert day==[r['reported_net_assets_eop'],r['reported_investor_accounts_eop'],r['reporting_at_cutoff']]
 assert r['reporting_at_cutoff']==60
extra={
 'eligible':rows('select Classificacao,count(*) n from eligible group by 1'),
 'cohort_daily':rows('select count(*) observations,count(distinct DT_COMPTC) dates,min(DT_COMPTC) first_date,max(DT_COMPTC) last_date from daily join cohort using(cnpj)'),
 'registry_duplicate_examples':rows('select ID_Registro_Fundo,count(*) n from fundo group by 1 having n>1 order by n desc limit 5'),
 'daily_duplicate_examples':rows('select TP_FUNDO_CLASSE,cnpj,ID_SUBCLASSE,DT_COMPTC,count(*) n from daily group by all having n>1 limit 5'),
 'cohort_missing_observed_dates':rows('with dates as (select distinct DT_COMPTC from daily) select count(*) missing_pairs from cohort cross join dates where not exists(select 1 from daily d where d.cnpj=cohort.cnpj and d.DT_COMPTC=dates.DT_COMPTC)'),
 'subclass_examples':rows('select cnpj,DT_COMPTC,count(*) n,count(distinct VL_PATRIM_LIQ) distinct_pl from daily where ID_SUBCLASSE is not null group by 1,2 having count(*)>1 order by 1,2 limit 5'),
 'daily_membership':rows('select TP_FUNDO_CLASSE,count(*) n,count(*) filter(where not exists(select 1 from classe c where c.CNPJ_Classe=d.cnpj)) no_class,count(*) filter(where not exists(select 1 from fundo f where f.CNPJ_Fundo=d.cnpj)) no_fund from daily d group by 1')
}
(P/'evidence/cohort-profile.json').write_text(json.dumps(extra,indent=2,default=str)+'\n')
(P/'evidence/monthly-oracles.json').write_text(json.dumps(oracles,indent=2,default=str)+'\n')
print(json.dumps({'oracles':oracles,'profile':extra},indent=2,default=str))

edge_queries={
 'duplicate_payloads': "select * from daily where cnpj='49963346000184' and DT_COMPTC in ('2026-07-07','2026-07-08') order by DT_COMPTC,VL_QUOTA",
 'cohort_gaps': "with dates as (select distinct DT_COMPTC from daily join cohort using(cnpj)) select cohort.cnpj,dates.DT_COMPTC from cohort cross join dates where not exists(select 1 from daily d where d.cnpj=cohort.cnpj and d.DT_COMPTC=dates.DT_COMPTC) order by 1,2",
 'extra_dates': "select distinct DT_COMPTC from daily except select distinct DT_COMPTC from daily join cohort using(cnpj)",
 'negative_cohort': "select count(*) filter(where cast(VL_PATRIM_LIQ as decimal(17,2))<0) negative_pl,count(*) filter(where cast(VL_QUOTA as decimal(27,12))<=0) nonpositive_quota from daily join cohort using(cnpj)",
 'subclass_unmatched': "select count(*) n from daily d where ID_SUBCLASSE is not null and not exists(select 1 from classe c join subclasse s using(ID_Registro_Classe) where c.CNPJ_Classe=d.cnpj and s.ID_Subclasse=d.ID_SUBCLASSE)"
}
(P/'evidence/edge-cases.json').write_text(json.dumps({k:rows(v) for k,v in edge_queries.items()},indent=2,default=str)+'\n')
calendar=rows('select distinct DT_COMPTC as date from daily join cohort using(cnpj) order by 1')
(P/'evidence/calendar.json').write_text(json.dumps(calendar,indent=2)+'\n')
