"""Fail-closed exercise mutations for disposable projects, including old baselines."""
import re
from pathlib import Path

import yaml


def remove_stock_rule(project):
    matches = []
    for path in sorted((Path(project) / 'models').rglob('*')):
        if path.suffix not in ('.yml', '.yaml'):
            continue
        original = path.read_bytes()
        document = yaml.safe_load(original) or {}
        for model in document.get('models', []):
            if model.get('name') != 'fct_daily':
                continue
            for metric in model.get('metrics', []):
                if metric.get('name') == 'reported_net_assets_eop':
                    matches.append((path, original, document, metric))
    if len(matches) != 1:
        raise ValueError('Expected exactly one PL metric definition')
    path, original, document, metric = matches[0]
    expected = {'name': 'report_date', 'window_agg': 'max', 'group_by': []}
    if metric.get('non_additive_dimension') != expected:
        raise ValueError('Expected intact common-closing-date rule')
    del metric['non_additive_dimension']
    path.write_text(yaml.safe_dump(document, sort_keys=False))
    return path, original


def replace_missing_pl(project):
    paths = list((Path(project) / 'models').rglob('fct_daily.sql'))
    if len(paths) != 1:
        raise ValueError('Expected exactly one fct_daily SQL model')
    path = paths[0]
    original = path.read_bytes()
    text = original.decode()
    pattern = r'\bd\.pl\s*::\s*decimal\(17,\s*2\)'
    if len(re.findall(pattern, text)) != 1:
        raise ValueError('Expected exactly one unmodified PL expression')
    path.write_text(re.sub(pattern, 'coalesce(d.pl, 0)::decimal(17, 2)', text))
    return path, original
