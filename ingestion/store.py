"""DuckDB landing schema and atomic batch registration, shared by CLI and fixtures."""
import json
DDL='''
create schema if not exists landing;
create table if not exists landing.raw_envelopes(capture_id varchar,source_id varchar,period varchar,payload varchar, primary key(capture_id,source_id));
create table if not exists landing.captures(capture_id varchar primary key,captured_at timestamptz);
create table if not exists landing.registry_cohort(cnpj varchar,entity_id varchar,classification_at_capture varchar);
create table if not exists landing.report_calendar(report_date date);
create table if not exists landing.files(capture_id varchar,file_sha256 varchar,member varchar,enveloped bigint,excluded bigint,primary key(capture_id,file_sha256));
create table if not exists landing.batches(capture_id varchar primary key,input_signature varchar);
'''
def register(c, capture_id, captured_at, signature, rows, entities, calendar, files):
    c.execute(DDL)
    c.execute('begin')
    try:
        old=c.execute('select input_signature from landing.batches where capture_id=?',[capture_id]).fetchone()
        if old:
            if old[0]!=signature:raise ValueError('Capture input changed')
            existing=c.execute('select capture_id,source_id,period,payload from landing.raw_envelopes where capture_id=?',[capture_id]).fetchall()
            if sorted(existing)!=sorted(rows):raise ValueError('Registered envelopes corrupted or parser output changed')
            c.execute('commit');return False
        # The population/calendar are fixed for this demo; changing either requires a new workspace.
        for table,expected in [('registry_cohort',entities),('report_calendar',calendar)]:
            existing=c.execute(f'select * from landing.{table}').fetchall()
            normalized=[tuple(str(v) for v in row) for row in expected]
            if existing and sorted(tuple(str(v) for v in r) for r in existing)!=sorted(normalized):raise ValueError('Frozen cohort/calendar changed')
            if not existing and expected:c.executemany(f'insert into landing.{table} values ({",".join("?" for _ in expected[0])})',expected)
        c.execute('insert into landing.captures values (?,?)',[capture_id,captured_at])
        if rows:c.executemany('insert into landing.raw_envelopes values (?,?,?,?)',rows)
        if files:c.executemany('insert into landing.files values (?,?,?,?,?)',files)
        c.execute('insert into landing.batches values (?,?)',[capture_id,signature])
        c.execute('commit');return True
    except BaseException:
        c.execute('rollback');raise
