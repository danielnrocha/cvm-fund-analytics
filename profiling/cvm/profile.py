"""Research-only CVM grain profiling and deterministic cohort oracles."""
import csv, decimal, json, pathlib
import duckdb
P=pathlib.Path(__file__).resolve().parent
c=duckdb.connect(str(P/'profile.duckdb'))
for table, paths in [('daily',sorted(p for p in (P/'extracted').glob('inf*/*.csv') if '.utf8.' not in p.name)), *[(t,[P/'extracted/registro_fundo_classe'/f'registro_{t}.csv']) for t in ['fundo','classe','subclasse']]]:
    # DuckDB UTF-8 input; original Latin-1 bytes retained untouched.
    converted=[]
    for p in paths:
        q=p.with_suffix('.utf8.csv'); q.write_text(p.read_bytes().decode('latin1'),encoding='utf8'); converted.append(str(q))
    c.execute(f'create or replace table {table} as select * from read_csv(?, delim=\';\', header=true, all_varchar=true)',[converted])
c.execute("alter table daily add column cnpj varchar")
c.execute("update daily set cnpj=regexp_replace(CNPJ_FUNDO_CLASSE,'[^0-9]','','g')")
def rows(sql):
    r=c.execute(sql); return [dict(zip([d[0] for d in r.description],row)) for row in r.fetchall()]
queries={
 'monthly':"select substr(DT_COMPTC,1,7) as period,count(*) as row_count,count(distinct cnpj) cnpjs,count(*) filter(where ID_SUBCLASSE is not null) subclass_rows,min(DT_COMPTC) first_date,max(DT_COMPTC) last_date from daily group by all order by 1",
 'types':'select TP_FUNDO_CLASSE,count(*) as row_count from daily group by all',
 'daily_duplicates':"select count(*) duplicate_groups from (select TP_FUNDO_CLASSE,cnpj,ID_SUBCLASSE,DT_COMPTC,count(*) n from daily group by all having n>1)",
 'registry_keys':"select 'fundo' entity,count(*) as row_count,count(distinct ID_Registro_Fundo) ids,count(distinct CNPJ_Fundo) cnpjs from fundo union all select 'classe',count(*),count(distinct ID_Registro_Classe),count(distinct CNPJ_Classe) from classe union all select 'subclasse',count(*),count(distinct ID_SUBCLASSE),count(distinct (ID_Registro_Classe,ID_SUBCLASSE)) from subclasse",
 'joins':"select TP_FUNDO_CLASSE,count(*) as row_count,count(*) filter(where c.ID_Registro_Classe is null) no_class,count(*) filter(where f.ID_Registro_Fundo is null) no_fund from daily d left join classe c on d.cnpj=c.CNPJ_Classe left join fundo f on d.cnpj=f.CNPJ_Fundo group by all",
 'orphans':"select (select count(*) from classe c left join fundo f using(ID_Registro_Fundo) where f.ID_Registro_Fundo is null) class_without_fund,(select count(*) from subclasse s left join classe c using(ID_Registro_Classe) where c.ID_Registro_Classe is null) subclass_without_class",
 'classifications':"select Classificacao,count(*) n from classe group by all order by n desc",
 'subclass_mixed':"select count(*) mixed_groups from (select cnpj,DT_COMPTC from daily group by all having count(*) filter(where ID_SUBCLASSE is null)>0 and count(*) filter(where ID_SUBCLASSE is not null)>0)",
 'multiple_subclasses':"select count(*) as group_count from (select cnpj,DT_COMPTC from daily group by all having count(distinct ID_SUBCLASSE)>1)",
 'hierarchy':"select count(*) multi_class_funds from (select ID_Registro_Fundo,count(*) n from classe group by all having n>1)"
}
out={k:rows(v) for k,v in queries.items()}
out['columns']=[]
for col in ['VL_TOTAL','VL_QUOTA','VL_PATRIM_LIQ','CAPTC_DIA','RESG_DIA','NR_COTST']:
    typ='decimal(27,12)' if col=='VL_QUOTA' else ('bigint' if col=='NR_COTST' else 'decimal(17,2)')
    out['columns']+=rows(f"select '{col}' name,count(*) filter(where {col} is null) nulls,count(*) filter(where {col} is not null and try_cast({col} as {typ}) is null) invalid,count(*) filter(where try_cast({col} as {typ})<0) negatives,min(try_cast({col} as {typ})) minimum,max(try_cast({col} as {typ})) maximum from daily")
(P/'evidence/profile.json').write_text(json.dumps(out,indent=2,default=str)+'\n')
print(json.dumps(out,indent=2,default=str))
