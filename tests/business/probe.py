"""Executable specification over reduced, synthetic, typed records.

No production ingestion, CVM parser, Vault or MetricFlow implementation.
"""
from collections import defaultdict
from decimal import Decimal
import re
import duckdb


def identity(row):
    cnpj = row['cnpj']
    if not isinstance(cnpj, str) or not re.fullmatch(r'(?:[0-9]{14}|[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2})', cnpj):
        raise ValueError('Invalid CNPJ representation')
    if row['kind'] not in ('CLASS', 'FUND'):
        raise ValueError('Unknown reporting namespace')
    sub = row['subclass']
    if sub is not None and (not isinstance(sub, str) or not sub or row['kind'] != 'CLASS'):
        raise ValueError('Invalid subclass scope')
    return row['kind'], re.sub(r'[^0-9]', '', cnpj), sub


def deduplicate(rows):
    groups = {}
    for row in rows:
        key = (row['capture'], identity(row), row['date'])
        payload = (Decimal(row['pl']), Decimal(row['flow']))
        if key in groups:
            previous = groups[key]
            if payload != (Decimal(previous['pl']), Decimal(previous['flow'])):
                raise ValueError('Conflicting payloads in same capture')
            if row['source'] not in previous['sources']:
                previous['sources'].append(row['source'])
        else:
            groups[key] = {**row, 'sources': [row['source']]}
    return list(groups.values())


def resolve(rows, registry):
    candidates = defaultdict(list)
    for record in registry:
        candidates[identity(record)].append(record['entity'])
    result = []
    for row in rows:
        matches = candidates[identity(row)]
        if len(matches) != 1:
            raise ValueError('Unknown or ambiguous identity')
        result.append({**row, 'entity': matches[0]})
    return result


def enrich(facts, dimension):
    lookup = defaultdict(list)
    for row in dimension:
        lookup[row['entity']].append(row)
    result = []
    for fact in facts:
        matches = lookup[fact['entity']]
        if len(matches) != 1:
            raise ValueError('Dimension join requires exactly one match')
        result.append({**matches[0], **fact})
    return result


def summarize(facts, entities, dates):
    if len(entities) != len(set(entities)) or len(dates) != len(set(dates)):
        raise ValueError('Population and calendar must be unique')
    selected = [r for r in facts if r['entity'] in entities and r['date'] in dates]
    keys = [(r['entity'], r['date']) for r in selected]
    if len(keys) != len(set(keys)):
        raise ValueError('Fact grain violated')
    with duckdb.connect(':memory:') as c:
        c.execute('create table facts(entity varchar, day date, pl decimal(17,2), flow decimal(38,2))')
        if selected:
            c.executemany('insert into facts values (?,?,?,?)', [(r['entity'], r['date'], r['pl'], r['flow']) for r in selected])
        cutoff = max(dates) if dates else None
        pl, flow, present, cutoff_present = c.execute('''select
            sum(pl) filter(where day = cast(? as date)), sum(flow), count(*),
            count(*) filter(where day = cast(? as date)) from facts''', [cutoff, cutoff]).fetchone()
    expected = len(entities) * len(dates)
    return dict(pl=pl, flow=flow, present=present, expected=expected,
                cutoff_present=cutoff_present, cutoff_expected=len(entities) if dates else 0,
                status='no_data' if not expected else ('complete' if present == expected else 'partial'))
