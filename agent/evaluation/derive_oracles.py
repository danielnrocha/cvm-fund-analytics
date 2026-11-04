"""Independent Decimal aggregation; imports no agent or MetricFlow implementation."""
import argparse
import hashlib
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path
import duckdb

p = argparse.ArgumentParser()
p.add_argument('--snapshot', type=Path, required=True)
p.add_argument('--dataset-dir', type=Path, required=True)
p.add_argument('--monthly-oracles', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
con = duckdb.connect(str(a.snapshot), read_only=True, config={
    'enable_external_access': 'false', 'autoload_known_extensions': 'false',
    'autoinstall_known_extensions': 'false'})
source_sql = 'SELECT entity_id, classification_at_capture, report_date, pl, net_flow, reported, expected FROM main.fct_daily ORDER BY report_date, entity_id'
columns = ['entity', 'classification', 'day', 'pl', 'flow', 'reported', 'expected']
data = [dict(zip(columns, row)) for row in con.execute(source_sql).fetchall()]
con.close()
assert len(data) == 7560 and sum(x['reported'] for x in data) == 7554
assert len({x['entity'] for x in data}) == 60

def total(rows, field):
    values = [r[field] for r in rows if r[field] is not None]
    return str(sum(values, Decimal(0))) if values else None

oracles = {}
for split in ('development', 'holdout'):
    dataset = json.loads((a.dataset_dir / (split + '.json')).read_text())
    for family in dataset['families']:
        queries = [q for q in family['expected'] if q['action'] == 'query']
        if not queries:
            continue
        assert len(queries) == 1
        q = queries[0]
        start, end = date.fromisoformat(q['start_date']), date.fromisoformat(q['end_date'])
        selected = [r for r in data if start <= r['day'] <= end]
        for f in q['filters']:
            field = {'reporting_entity': 'entity', 'classification_at_capture': 'classification'}[f['field']]
            selected = [r for r in selected if r[field] in f['values']]
        groups = defaultdict(list)
        for r in selected:
            key = []
            if q['grain'] != 'total':
                day = r['day'].replace(day=1) if q['grain'] == 'month' else r['day']
                key.append(('metric_time__' + q['grain'], day.isoformat()))
            for dimension in q['dimensions']:
                assert dimension == 'reporting_entity'
                key.append((dimension, r['entity']))
            groups[tuple(key)].append(r)
        rows = []
        for group, observations in sorted(groups.items()):
            cut = max(r['day'] for r in observations)
            closing = [r for r in observations if r['day'] == cut]
            end_counts = [sum(r['reported'] for r in closing), sum(r['expected'] for r in closing)]
            interval_counts = [sum(r['reported'] for r in observations), sum(r['expected'] for r in observations)]
            values, counts, support = {}, {}, {}
            for metric in q['metrics']:
                is_closing = metric in ('reported_net_assets_eop', 'reporting_coverage_eop')
                pair = end_counts if is_closing else interval_counts
                counts[metric] = pair
                names = ('reporting_entities_eop', 'expected_entities_eop') if is_closing else ('reporting_observations', 'expected_observations')
                support.update(zip(names, pair))
                if metric == 'reported_net_assets_eop':
                    values[metric] = total(closing, 'pl')
                elif metric == 'net_flow':
                    values[metric] = total(observations, 'flow')
                else:
                    assert metric in ('reporting_coverage_eop', 'reporting_coverage_period')
                    values[metric] = str(Decimal(pair[0]) / Decimal(pair[1])) if pair[1] else None
            rows.append({'group': dict(group), 'effective_cut': cut.isoformat(), 'values': values,
                         'counts': counts, 'supporting_counts': support})
        if not rows:
            status = 'no_expected_observations' if not any(start <= r['day'] <= end for r in data) else 'empty'
        else:
            status = 'partial' if any(n != d for row in rows for n, d in row['counts'].values()) else 'ok'
        oracles[family['family']] = {'status': status, 'rows': rows}

assert Decimal(oracles['D01']['rows'][0]['values']['reported_net_assets_eop']) == Decimal('119385193058.06')
assert Decimal(oracles['D02']['rows'][0]['values']['net_flow']) == Decimal('4725910556.15')
for row, old in zip(oracles['D03']['rows'], json.loads(a.monthly_oracles.read_text()), strict=True):
    assert row['effective_cut'] == old['cutoff']
    for metric in ('reported_net_assets_eop', 'net_flow'):
        assert Decimal(row['values'][metric]) == Decimal(old[metric])
assert all(v is None for v in oracles['D07']['rows'][0]['values'].values())
assert oracles['H15']['rows'][0]['values']['reporting_coverage_eop'] == '0'
assert oracles['H05'] == {'status': 'no_expected_observations', 'rows': []}
a.output.write_text(json.dumps(oracles, indent=2, sort_keys=True) + '\n')
evidence = {'source_sql': source_sql, 'source_snapshot_sha256': hashlib.sha256(a.snapshot.read_bytes()).hexdigest(),
            'derivation_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'output_sha256': hashlib.sha256(a.output.read_bytes()).hexdigest(),
            'families': len(oracles), 'rows': sum(len(x['rows']) for x in oracles.values()),
            'method': 'Independent Python Decimal aggregation of sealed fact rows; no MetricFlow or agent imports; frozen published monthly and full-period oracles cross-checked.'}
a.output.with_suffix('.evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
print(json.dumps(evidence))
