import hashlib,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from ci.docs import verify_driver
class DriverIntegrity(unittest.TestCase):
 def test_wrong_binary_is_rejected_even_at_expected_size(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'driver.so';p.write_bytes(b'bad')
   with self.assertRaises(ValueError):verify_driver(p,{'size':3,'sha256':hashlib.sha256(b'good').hexdigest()})
 def test_missing_binary_is_rejected(self):
  with self.assertRaises(ValueError):verify_driver(pathlib.Path('/nonexistent/driver.so'),{'size':3,'sha256':'x'})
 def test_verified_binary_is_accepted(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'driver.so';p.write_bytes(b'good');digest=hashlib.sha256(b'good').hexdigest()
   self.assertEqual(verify_driver(p,{'size':4,'sha256':digest}),digest)

class DriverBootstrap(unittest.TestCase):
 def fixture(self,root):
  packed=bytes.fromhex('28b52ffd0458210000676f6f64b751e0fd');source=root/'source.zst';source.write_bytes(packed)
  return {'url':source.as_uri(),'compressed_size':len(packed),'compressed_sha256':hashlib.sha256(packed).hexdigest(),'size':4,'sha256':hashlib.sha256(b'good').hexdigest(),'filename':'driver.so'}
 def test_exact_download_is_verified_and_unpacked(self):
  from ci.docs import prepare
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);lock=self.fixture(root);prepare(lock,root/'dest')
   self.assertTrue((root/'dest/driver.so').exists());self.assertEqual((root/'dest/driver.so').read_bytes(),b'good')
 def test_compressed_drift_never_writes_driver(self):
  from ci.docs import prepare
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);lock=self.fixture(root);lock['compressed_sha256']='0'*64
   with self.assertRaises(ValueError):prepare(lock,root/'dest')
   self.assertFalse((root/'dest/driver.so').exists())
 def test_unpacked_drift_never_writes_driver(self):
  from ci.docs import prepare
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);lock=self.fixture(root);lock['sha256']='0'*64
   with self.assertRaises(ValueError):prepare(lock,root/'dest')
   self.assertFalse((root/'dest/driver.so').exists())

class V2Documentation(unittest.TestCase):
 def test_v2_html_and_parquet_do_not_require_legacy_catalog(self):
  from ci.docs import verify_documentation
  import duckdb
  with tempfile.TemporaryDirectory() as d:
   root=pathlib.Path(d);(root/'info_schema/v1').mkdir(parents=True)
   (root/'index.html').write_text('<!doctype html><title>dbt docs v2</title>')
   with duckdb.connect() as c:
    c.execute('copy (select 1 as model) to ? (format parquet)',[str(root/'info_schema/v1/dbt.models.parquet')])
   self.assertEqual(verify_documentation(root),1)
 def test_missing_generated_html_rejected(self):
  from ci.docs import verify_documentation
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):verify_documentation(pathlib.Path(d))
