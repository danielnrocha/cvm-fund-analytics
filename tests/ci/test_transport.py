"""Model ZIP transport using the pinned upload action's hidden-file setting.

This verifies sealed content survives that selection; it is not a GitHub run.
"""
import json
import pathlib
import sys
import tempfile
import unittest
import zipfile
import yaml
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from release.snapshots import seal, _verify

class ArtifactTransport(unittest.TestCase):
    def test_workflow_roundtrip_retains_sealed_hidden_content(self):
        workflow = pathlib.Path(__file__).resolve().parents[2] / '.github/workflows/linux-ci.yml'
        steps = yaml.safe_load(workflow.read_text())['jobs']['validate']['steps']
        upload = next(s for s in steps if s.get('uses', '').startswith('actions/upload-artifact@'))
        include_hidden = upload['with'].get('include-hidden-files', False)
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            candidate = root / 'candidate'
            (candidate / 'project/target/private/index').mkdir(parents=True)
            (candidate / 'snapshot.duckdb').write_bytes(b'closed fixture')
            (candidate / 'validation.json').write_text(json.dumps({'passed': True}))
            for name in ('project/.gitignore', 'project/.user.yml', 'project/target/private/index/.artifact_meta.json'):
                (candidate / name).write_text('sealed hidden bytes')
            seal(root / 'output/releases', candidate, 'baseline')
            with zipfile.ZipFile(root / 'artifact.zip', 'w') as archive:
                for file in (root / 'output').rglob('*'):
                    relative = file.relative_to(root / 'output')
                    if file.is_file() and (include_hidden or not any(p.startswith('.') for p in relative.parts)):
                        archive.write(file, relative)
            with zipfile.ZipFile(root / 'artifact.zip') as archive:
                archive.extractall(root / 'download')
            restored = _verify(root / 'download/releases', 'baseline')
            self.assertEqual((restored / 'project/.user.yml').read_text(), 'sealed hidden bytes')
