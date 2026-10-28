"""Assertions for the frozen profiling evidence, not production data tests."""
from pathlib import Path
import hashlib,json,duckdb
p=Path(__file__).resolve().parent
c=duckdb.connect(str(p/'profile.duckdb'))
def scalar(sql):return c.execute(sql).fetchone()[0]
checks={
 'source_hashes':all(hashlib.sha256((p/r['file']).read_bytes()).hexdigest()==r['sha256'] for r in json.loads((p/'evidence/sources.json').read_text())),
 'daily_count':scalar('select count(*) from daily')==3227984,
 'cohort_count':scalar('select count(*) from cohort')==60,
 'cohort_observations':scalar('select count(*) from daily join cohort using(cnpj)')==7554,
 'calendar_count':len(json.loads((p/'evidence/calendar.json').read_text()))==126,
 'six_internal_gaps':len(json.loads((p/'evidence/edge-cases.json').read_text())['cohort_gaps'])==6,
 'all_monthly_cutoffs_full':all(r['reporting_at_cutoff']==60 for r in json.loads((p/'evidence/monthly-oracles.json').read_text())),
 'cohort_grain':scalar('select count(*)=count(distinct (cnpj,DT_COMPTC)) from daily join cohort using(cnpj)'),
 'no_subclasses':scalar('select count(*) from daily join cohort using(cnpj) where ID_SUBCLASSE is not null')==0,
 'non_null_daily_keys':scalar('select count(*) from daily where TP_FUNDO_CLASSE is null or cnpj is null or DT_COMPTC is null')==0,
 'normalized_cnpj_shape':scalar("select count(*) from daily where not regexp_full_match(cnpj,'[0-9]{14}')")==0,
 'dates_in_filename_month':True
}
for f in sorted((p/'extracted').glob('inf*/*.utf8.csv')):
 if '.utf8.utf8.' in f.name:continue
 month=f.name.split('_')[-1].split('.')[0]
 checks['dates_in_filename_month'] &= c.execute("select count(*) from read_csv(?,delim=';',all_varchar=true) where replace(substr(DT_COMPTC,1,7),'-','')<>?",[str(f),month]).fetchone()[0]==0
(p/'evidence/validation.json').write_text(json.dumps(checks,indent=2)+'\n')
assert all(checks.values()),checks
print(f'{len(checks)} frozen-snapshot assertions passed')
