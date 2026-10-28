import hashlib,json,os,pathlib,sys,tempfile,unittest,zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from ci.baseline import pack,restore
from release.snapshots import seal,_verify

class DurableBaseline(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
  candidate=self.root/'candidate';(candidate/'project').mkdir(parents=True)
  (candidate/'snapshot.duckdb').write_bytes(b'closed-db')
  (candidate/'validation.json').write_text('{"passed":true}')
  (candidate/'project/.hidden').write_text('required')
  seal(self.root/'source',candidate,'approved')
 def tearDown(self):self.temp.cleanup()
 def archive(self):
  archive=self.root/'baseline.zip';lock=pack(self.root/'source','approved',archive,'baseline-v1');return archive,lock
 def test_roundtrip_preserves_hidden_files_and_bundle_integrity(self):
  archive,lock=self.archive();restore(archive,lock,self.root/'restored')
  self.assertEqual((_verify(self.root/'restored','approved')/'project/.hidden').read_text(),'required')
 def test_changed_archive_rejected_before_destination_created(self):
  archive,lock=self.archive();archive.write_bytes(archive.read_bytes()+b'drift')
  with self.assertRaises(ValueError):restore(archive,lock,self.root/'restored')
  self.assertFalse((self.root/'restored').exists())
 def test_deterministic_pack_is_independent_of_file_timestamps(self):
  archive,lock=self.archive()
  os.utime(self.root/'source/snapshots/approved/project/.hidden',(1700000000,1700000000))
  other=pack(self.root/'source','approved',self.root/'other.zip','baseline-v1')
  self.assertEqual(lock['sha256'],other['sha256'])
 def test_path_traversal_rejected_even_with_matching_archive_hash(self):
  archive,lock=self.archive()
  with zipfile.ZipFile(archive,'a') as z:z.writestr('../escaped','bad')
  lock.update(size=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
  with self.assertRaises(ValueError):restore(archive,lock,self.root/'restored')
  self.assertFalse((self.root/'escaped').exists());self.assertFalse((self.root/'restored').exists())
 def test_wrong_release_id_fails_closed(self):
  archive,lock=self.archive();lock['release_id']='different'
  with self.assertRaises(ValueError):restore(archive,lock,self.root/'restored')
  self.assertFalse((self.root/'restored').exists())
 def test_existing_destination_not_replaced(self):
  archive,lock=self.archive();dest=self.root/'restored';dest.mkdir();(dest/'keep').write_text('mine')
  with self.assertRaises(FileExistsError):restore(archive,lock,dest)
  self.assertEqual((dest/'keep').read_text(),'mine')
 def test_corrupted_inner_bundle_rejected_even_if_archive_hash_matches(self):
  archive,lock=self.archive()
  with zipfile.ZipFile(archive) as z:files={n:z.read(n) for n in z.namelist()}
  files['snapshots/approved/snapshot.duckdb']=b'corrupted'
  with zipfile.ZipFile(archive,'w') as z:
   for n,b in files.items():z.writestr(n,b)
  lock.update(size=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
  with self.assertRaises(ValueError):restore(archive,lock,self.root/'restored')
  self.assertFalse((self.root/'restored').exists())
