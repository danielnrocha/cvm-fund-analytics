import hashlib,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from ci.fetch_inputs import fetch
class FrozenInputs(unittest.TestCase):
 def test_fetch_exact_bytes_without_changing_pin(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);source=root/'source';source.write_bytes(b'pinned')
   manifest=[{'file':'raw/input','url':source.as_uri(),'bytes':6,'sha256':hashlib.sha256(b'pinned').hexdigest()}]
   fetch(manifest,root)
   self.assertTrue((root/'raw/input').exists())
   self.assertEqual((root/'raw/input').read_bytes(),b'pinned')
 def test_drift_never_persists_download(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);source=root/'source';source.write_bytes(b'changed')
   with self.assertRaises(ValueError):fetch([{'file':'raw/input','url':source.as_uri(),'bytes':6,'sha256':hashlib.sha256(b'pinned').hexdigest()}],root)
   self.assertFalse((root/'raw/input').exists())
 def test_corrupted_cache_is_rejected_without_overwrite(self):
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);(root/'input').write_bytes(b'bad')
   with self.assertRaises(ValueError):fetch([{'file':'input','url':'unused','bytes':6,'sha256':hashlib.sha256(b'pinned').hexdigest()}],root)
   self.assertEqual((root/'input').read_bytes(),b'bad')
 def test_escape_path_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):fetch([{'file':'../outside'}],pathlib.Path(d))
