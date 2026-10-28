"""Transport only: preserve each external JSONL line, even when malformed."""
from pathlib import Path
import hashlib
import duckdb
p=Path(__file__).resolve().parent
raw=(p/'fixtures/external.jsonl').read_bytes()
rows=[(hashlib.sha256(raw).hexdigest(), i, line) for i,line in enumerate(raw.decode().splitlines(),1)]
with duckdb.connect(str(p/'probe.duckdb')) as c:
    c.execute('create or replace table main.raw_json_fixture(file_sha256 varchar, line_number integer, payload varchar)')
    c.executemany('insert into main.raw_json_fixture values (?,?,?)',rows)
