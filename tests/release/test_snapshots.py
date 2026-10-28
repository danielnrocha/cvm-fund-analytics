import sys,pathlib,tempfile,json,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from release.snapshots import seal,promote as actual_promote,resolve,rollback
from release import uat
from unittest.mock import patch

def promote(root,environment,release_id,expected=None):
 # Snapshot tests isolate the external MetricFlow boundary; UAT failures have their own suite.
 gate=None
 if environment=='uat':
  def tables(bundle):
   return {name:','.join([*s['keys'],*s['metrics'].split(',')])+'\n'+','.join(['group']*len(s['keys'])+['10']*len(s['metrics'].split(',')))+'\n' for name,s in uat.QUERIES.items()}
  with patch.object(uat,'collect',side_effect=tables):gate=uat.evaluate(root,expected or release_id,release_id,bootstrap=expected is None)
 return actual_promote(root,environment,release_id,expected,gate=gate)
class Snapshots(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def candidate(self,name='a',valid=True):
  p=self.root/('candidate-'+name);p.mkdir();(p/'snapshot.duckdb').write_bytes(name.encode())
  (p/'validation.json').write_text(json.dumps({'passed':valid,'source_hashes':{k:'frozen' for k in uat.INPUTS}}))
  return p
 def test_seal_and_promote_preserve_complete_bundle(self):
  p=seal(self.root,self.candidate(),'a');self.assertIsNotNone(p)
  promote(self.root,'dev','a');self.assertEqual(resolve(self.root,'dev'),p)
  self.assertEqual((p/'snapshot.duckdb').read_bytes(),b'a')
 def test_failed_candidate_never_replaces_current(self):
  seal(self.root,self.candidate(),'a');promote(self.root,'uat','a')
  with self.assertRaises(ValueError):seal(self.root,self.candidate('bad',False),'bad')
  self.assertIsNotNone(resolve(self.root,'uat'));self.assertEqual(resolve(self.root,'uat').name,'a')
 def test_env_pointers_are_independent(self):
  seal(self.root,self.candidate(),'a');seal(self.root,self.candidate('b'),'b')
  promote(self.root,'dev','a');promote(self.root,'uat','a');promote(self.root,'dev','b',expected='a')
  self.assertIsNotNone(resolve(self.root,'uat'));self.assertEqual(resolve(self.root,'uat').name,'a');self.assertEqual(resolve(self.root,'dev').name,'b')
 def test_stale_promotion_rejected(self):
  seal(self.root,self.candidate(),'a');seal(self.root,self.candidate('b'),'b');promote(self.root,'dev','a')
  with self.assertRaises(ValueError):promote(self.root,'dev','b',expected=None)
 def test_rollback_returns_previous_exact_bytes(self):
  seal(self.root,self.candidate(),'a');seal(self.root,self.candidate('b'),'b')
  promote(self.root,'uat','a');promote(self.root,'uat','b',expected='a');rollback(self.root,'uat',expected='b')
  self.assertIsNotNone(resolve(self.root,'uat'));self.assertEqual((resolve(self.root,'uat')/'snapshot.duckdb').read_bytes(),b'a')
 def test_corrupted_bundle_blocks_promotion(self):
  p=seal(self.root,self.candidate(),'a');self.assertIsNotNone(p)
  (p/'snapshot.duckdb').chmod(0o644);(p/'snapshot.duckdb').write_bytes(b'bad')
  with self.assertRaises(ValueError):promote(self.root,'dev','a')
 def test_invalid_names_and_environment_are_rejected(self):
  for env in ['prod','../dev']:
   with self.assertRaises(ValueError):promote(self.root,env,'../escape')
 def test_existing_release_cannot_be_overwritten(self):
  seal(self.root,self.candidate(),'a')
  with self.assertRaises(ValueError):seal(self.root,self.candidate('second'),'a')

class AtomicFailures(unittest.TestCase):
 setUp=Snapshots.setUp
 tearDown=Snapshots.tearDown
 candidate=Snapshots.candidate
 def test_pointer_replace_failure_keeps_prior_snapshot(self):
  from unittest.mock import patch
  seal(self.root,self.candidate(),'a');seal(self.root,self.candidate('b'),'b');promote(self.root,'uat','a')
  with patch('release.snapshots.os.replace',side_effect=OSError('disk failure')):
   with self.assertRaises(OSError):promote(self.root,'uat','b',expected='a')
  self.assertEqual(resolve(self.root,'uat').name,'a')
 def test_readers_pin_old_snapshot_across_promotion(self):
  seal(self.root,self.candidate(),'a');seal(self.root,self.candidate('b'),'b');promote(self.root,'uat','a')
  pinned=resolve(self.root,'uat');promote(self.root,'uat','b',expected='a')
  self.assertEqual((pinned/'snapshot.duckdb').read_bytes(),b'a')
  self.assertEqual((resolve(self.root,'uat')/'snapshot.duckdb').read_bytes(),b'b')

class IntegrityGaps(unittest.TestCase):
 setUp=Snapshots.setUp
 tearDown=Snapshots.tearDown
 candidate=Snapshots.candidate
 def test_nested_manifest_is_hashed(self):
  candidate=self.candidate();(candidate/'project').mkdir();(candidate/'project/bundle.json').write_text('old')
  p=seal(self.root,candidate,'a');nested=p/'project/bundle.json';nested.chmod(0o644);nested.write_text('changed')
  with self.assertRaises(ValueError):promote(self.root,'dev','a')
 def test_nested_model_is_in_source_fingerprint(self):
  from unittest.mock import patch
  from scripts import snapshot
  p=self.root/'transform/models/nested';p.mkdir(parents=True);(p/'model.sql').write_text('select 1')
  with patch.object(snapshot,'ROOT',self.root):
   self.assertIn('transform/models/nested/model.sql',snapshot.source_hashes())

class CopyBinding(unittest.TestCase):
 def test_source_edit_during_copy_never_reaches_validation_or_sealing(self):
  from unittest.mock import patch
  from scripts import snapshot
  import shutil
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);source=root/'transform/models/nested';source.mkdir(parents=True)
   (source/'model.sql').write_text('select 1')
   original=shutil.copytree
   def race(*args,**kwargs):
    result=original(*args,**kwargs)
    (source/'model.sql').write_text('select 2')
    return result
   with patch.object(snapshot,'ROOT',root),patch.object(snapshot.shutil,'copytree',side_effect=race),patch.object(snapshot.subprocess,'run',side_effect=AssertionError('Validation must not run')):
    with self.assertRaisesRegex(ValueError,'Source changed during copy'):snapshot.build(root/'releases','dev','race')
   self.assertFalse((root/'releases/snapshots/race').exists())

if __name__=='__main__':unittest.main()
