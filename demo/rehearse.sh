#!/bin/bash
# Run from the repository root after prepare/reset. No downloads or promotion.
set -euo pipefail
REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "$REPO_ROOT/data/demo/env.sh"
if [ "$#" -eq 0 ]; then
  # macOS cannot nest sandbox-exec. Query/build steps and docs each get their own sandbox.
  /usr/bin/sandbox-exec -p '(version 1)(allow default)(deny network*)' /bin/bash "$DEMO_ROOT/demo/rehearse.sh" --offline-steps
  "$PY" "$DEMO_ROOT/compatibility/dbt-v2-metricflow/pinned_docs.py" --project .
  echo 'Both red/green exercises, real oracles, lineage and pinned docs passed.'
  exit 0
fi
if [ "$#" -ne 1 ] || [ "$1" != --offline-steps ]; then
  echo 'Usage: bash demo/rehearse.sh'; exit 2
fi
"$DBT" build --profiles-dir . --static-analysis strict --generate-info-schema
"$MF" validate-configs
"$PY" "$DEMO_ROOT/scripts/check_semantics.py"
# Exercise 1: the existing native unit fixture is the independent expectation.
"$PY" - <<'PY'
import os, sys
from pathlib import Path
sys.path.insert(0, os.environ['DEMO_ROOT'])
from demo.mutations import replace_missing_pl
p, original = replace_missing_pl(Path('.'))
Path('evidence/original-fct.sql').write_bytes(original)
PY
if "$DBT" test --profiles-dir . --select dense_calendar_keeps_missing_distinct_from_zero 2>&1 | tee evidence/expected-unit-failure.log; then
  echo 'ERROR: broken SQL unexpectedly passed'; exit 1
fi
"$PY" - <<'PY'
import json
from pathlib import Path
r=json.loads(Path('target/run_results.json').read_text())['results']
assert len(r)==1 and r[0]['status'] in ('fail','error') and 'dense_calendar_keeps_missing_distinct_from_zero' in r[0]['unique_id'],r
log=Path('evidence/expected-unit-failure.log').read_text()
assert 'Test failed: dense_calendar_keeps_missing_distinct_from_zero' in log and 'NULL -> 0.0' in log
Path('models/marts/fct_daily.sql').write_bytes(Path('evidence/original-fct.sql').read_bytes())
PY
"$DBT" test --profiles-dir . --select dense_calendar_keeps_missing_distinct_from_zero
# Exercise 2: valid YAML/SQL is not sufficient for a correct stock aggregation.
"$PY" - <<'PY'
import os, sys
from pathlib import Path
sys.path.insert(0, os.environ['DEMO_ROOT'])
from demo.mutations import remove_stock_rule
p, original = remove_stock_rule(Path('.'))
Path('evidence/original-semantic.yml').write_bytes(original)
PY
"$DBT" parse --profiles-dir .
"$MF" query --metrics reported_net_assets_eop,net_flow --csv evidence/broken-total.csv
if "$PY" "$DEMO_ROOT/scripts/check_semantics.py" > evidence/expected-semantic-failure.log 2>&1; then
  echo 'ERROR: broken semantic rule unexpectedly passed'; exit 1
fi
"$PY" - <<'PY'
import csv
from decimal import Decimal
from pathlib import Path
r=next(csv.DictReader(Path('evidence/broken-total.csv').open()))
assert Decimal(r['reported_net_assets_eop'])!=Decimal('119385193058.06'),r
assert Decimal(r['net_flow'])==Decimal('4725910556.15'),r
# The oracle must reject this stock value, not a query timeout or parser error.
assert "AssertionError: ('reported_net_assets_eop'," in Path('evidence/expected-semantic-failure.log').read_text()
monthly=list(csv.DictReader(Path('evidence/semantic-monthly.csv').open()))
assert len(monthly)==6
assert Decimal(next(x for x in monthly if x['metric_time__month'].startswith('2026-09'))['reported_net_assets_eop']) != Decimal('119385193058.06')
Path('models/marts/semantic.yml').write_bytes(Path('evidence/original-semantic.yml').read_bytes())
PY
"$DBT" parse --profiles-dir .
"$MF" query --metrics reported_net_assets_eop,net_flow --csv evidence/correct-total.csv
"$PY" "$DEMO_ROOT/scripts/check_semantics.py"
"$DBT" compile --profiles-dir . --static-analysis strict --generate-info-schema
"$PY" - <<'PY'
import os,sys
from pathlib import Path
sys.path.insert(0,os.environ['DEMO_ROOT'])
from ci.artifacts import check_lineage
print('Required column edges:',check_lineage(Path('target/info_schema/v1/dbt.column_lineage.parquet')))
PY
echo 'Offline build, queries and lineage passed.'
