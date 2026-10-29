"""Mutations must target the business rule, never a YAML position or stale path."""
import tempfile
import unittest
from pathlib import Path
import yaml


class MutationTests(unittest.TestCase):
    def test_stock_mutation_finds_rule_in_both_layouts_and_keeps_other_metrics(self):
        from demo.mutations import remove_stock_rule
        for relative in ('models/semantic.yml', 'models/marts/semantic.yml'):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                path = root / relative
                path.parent.mkdir(parents=True)
                rule = {'name': 'report_date', 'window_agg': 'max', 'group_by': []}
                content = {'models': [
                    {'name': 'time_spine'},
                    {'name': 'fct_daily', 'metrics': [
                        {'name': 'expected_entities_eop', 'non_additive_dimension': rule},
                        {'name': 'reported_net_assets_eop', 'non_additive_dimension': rule}]}]}
                path.write_text(yaml.safe_dump(content))
                original = path.read_bytes()
                found, saved = remove_stock_rule(root)
                self.assertEqual((found, saved), (path, original))
                metrics = yaml.safe_load(path.read_text())['models'][1]['metrics']
                self.assertEqual(metrics[0]['non_additive_dimension'], rule)
                self.assertNotIn('non_additive_dimension', metrics[1])
                mutated = path.read_bytes()
                with self.assertRaises(ValueError):
                    remove_stock_rule(root)
                self.assertEqual(path.read_bytes(), mutated)

    def test_duplicate_metric_definitions_fail_without_editing(self):
        from demo.mutations import remove_stock_rule
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'models').mkdir()
            content = {'models': [{'name': 'fct_daily', 'metrics': [
                {'name': 'reported_net_assets_eop', 'non_additive_dimension':
                 {'name': 'report_date', 'window_agg': 'max', 'group_by': []}}]}]}
            paths = [root / 'models/a.yml', root / 'models/b.yml']
            for path in paths:
                path.write_text(yaml.safe_dump(content))
            before = [p.read_bytes() for p in paths]
            with self.assertRaises(ValueError):
                remove_stock_rule(root)
            self.assertEqual([p.read_bytes() for p in paths], before)

    def test_pl_mutation_handles_formatter_spacing_and_refuses_noop(self):
        from demo.mutations import replace_missing_pl
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = root / 'models/marts/fct_daily.sql'
            path.parent.mkdir(parents=True)
            path.write_text('select d.pl::decimal(17, 2) as pl from daily as d\n')
            original = path.read_bytes()
            found, saved = replace_missing_pl(root)
            self.assertEqual((found, saved), (path, original))
            self.assertIn('coalesce(d.pl, 0)', path.read_text())
            mutated = path.read_bytes()
            with self.assertRaises(ValueError):
                replace_missing_pl(root)
            self.assertEqual(path.read_bytes(), mutated)
