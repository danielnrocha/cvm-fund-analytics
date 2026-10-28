"""Literal frozen-profile expectations, independent of model SQL."""
from pathlib import Path
from decimal import Decimal
import json,duckdb,os
ROOT=Path(__file__).resolve().parents[1]
with duckdb.connect(os.environ.get('CVM_DB_PATH',str(ROOT/'transform/cvm_demo.duckdb')),read_only=True) as c:
    assert c.execute('select count(*) from fct_daily').fetchone()[0]==7560, 'Expected dense frozen cohort: 7560 pairs'
    for r in json.loads((ROOT/'profiling/cvm/evidence/monthly-oracles.json').read_text()):
        actual=c.execute('''select sum(pl) filter(where report_date=?),sum(net_flow),sum(reported),
            sum(reported) filter(where report_date=?) from fct_daily where strftime(report_date,'%Y-%m')=?''',
            [r['cutoff'],r['cutoff'],r['period']]).fetchone()
        assert actual==(Decimal(r['reported_net_assets_eop']),Decimal(r['net_flow']),r['observations'],60),(r['period'],actual)
print('Six real monthly oracles and 7560 dense pairs PASS')
