"""Lifecycle regressions: never delete user files or mutate the source database."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE = Path(__file__).resolve().parents[2] / 'demo/workspace.py'

class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(MODULE.exists(), 'Disposable workspace lifecycle is not implemented')
        spec = importlib.util.spec_from_file_location('workspace', MODULE)
        self.api = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.api)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / 'transform'
        (self.project / 'models').mkdir(parents=True)
        (self.project / 'models/fct_daily.sql').write_text('original SQL')
        (self.project / 'models/semantic.yml').write_text('original YAML')
        (self.project / 'dbt_project.yml').write_text('name: test')
        self.database = self.root / 'baseline.duckdb'
        self.database.write_bytes(b'closed database fixture')

    def prepare(self):
        return self.api.prepare(self.root, self.database)

    def test_reset_restores_database_and_models_without_touching_source(self):
        work = self.prepare()
        (work / 'demo.duckdb').write_bytes(b'changed')
        (work / 'project/models/fct_daily.sql').write_text('broken SQL')
        self.api.reset(self.root, self.database)
        self.assertEqual((work / 'demo.duckdb').read_bytes(), b'closed database fixture')
        self.assertEqual((work / 'project/models/fct_daily.sql').read_text(), 'original SQL')
        self.assertEqual(self.database.read_bytes(), b'closed database fixture')
        self.assertEqual((self.project / 'models/fct_daily.sql').read_text(), 'original SQL')

    def test_prepare_refuses_to_overwrite_existing_workspace(self):
        work = self.prepare()
        (work / 'notes.txt').write_text('keep')
        with self.assertRaises((ValueError, FileExistsError)):
            self.prepare()
        self.assertEqual((work / 'notes.txt').read_text(), 'keep')

    def test_reset_refuses_unowned_directory(self):
        work = self.root / 'data/demo'
        work.mkdir(parents=True)
        (work / 'notes.txt').write_text('keep')
        with self.assertRaises(ValueError):
            self.api.reset(self.root, self.database)
        self.assertEqual((work / 'notes.txt').read_text(), 'keep')

    def test_reset_refuses_symlink_workspace_or_parent(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (outside / 'keep').write_text('keep')
        (self.root / 'data').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertEqual((outside / 'keep').read_text(), 'keep')

    def test_reset_refuses_symlink_inside_owned_workspace(self):
        work = self.prepare()
        (work / 'external').symlink_to(self.project, target_is_directory=True)
        with self.assertRaises(ValueError):
            self.api.reset(self.root, self.database)
        self.assertTrue((self.project / 'models/fct_daily.sql').exists())

    def test_failed_reset_preserves_workspace_when_source_project_is_invalid(self):
        work = self.prepare()
        (work / 'notes.txt').write_text('rehearsal notes')
        (self.project / 'external').symlink_to(self.database)
        with self.assertRaises(ValueError):
            self.api.reset(self.root, self.database)
        self.assertEqual((work / 'notes.txt').read_text(), 'rehearsal notes')

    def test_prepare_rejects_source_database_with_wal(self):
        Path(str(self.database) + '.wal').write_bytes(b'writer')
        with self.assertRaises(ValueError):
            self.prepare()
        self.assertFalse((self.root / 'data/demo').exists())

if __name__ == '__main__':
    unittest.main()
