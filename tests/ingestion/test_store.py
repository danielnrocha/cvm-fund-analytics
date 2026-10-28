import pathlib,sys,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
import duckdb
from ingestion.store import register
class Store(unittest.TestCase):
 def setUp(self):self.c=duckdb.connect(':memory:')
 def tearDown(self):self.c.close()
 def load(self,rows=None,signature='sig'):
  return register(self.c,'v1','2026-10-01T12:00:00+00:00',signature,rows if rows is not None else [('v1','s1','202604','{}')],[('00000000000100','A','RF')],[('2026-04-01',)],[('v1','sha','file',1,0)])
 def test_replay_is_idempotent(self):
  self.assertTrue(self.load());self.assertFalse(self.load())
  self.assertEqual(self.c.execute('select count(*) from landing.raw_envelopes').fetchone()[0],1)
 def test_changed_signature_rejected_without_writes(self):
  self.load()
  with self.assertRaises(ValueError):self.load(signature='changed')
  self.assertEqual(self.c.execute('select payload from landing.raw_envelopes').fetchone()[0],'{}')
 def test_duplicate_source_rolls_back_whole_batch(self):
  with self.assertRaises(Exception):self.load([('v1','s1','202604','{}'),('v1','s1','202604','{}')])
  self.assertEqual(self.c.execute('select count(*) from landing.captures').fetchone()[0],0)
  self.assertEqual(self.c.execute('select count(*) from landing.raw_envelopes').fetchone()[0],0)
 def test_replay_detects_missing_registered_envelope(self):
  self.load();self.c.execute('delete from landing.raw_envelopes')
  with self.assertRaises(ValueError):self.load()
if __name__=='__main__':unittest.main()
