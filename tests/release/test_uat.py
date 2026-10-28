"""Business failures: shifted values, missing groups, null substitution and stale attestations."""
import csv,io,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from release import uat
from release.snapshots import seal,promote,resolve
class SemanticDiff(unittest.TestCase):
 def diff(self,a,b,keys=('period',)):
  return uat.compare_csv(a,b,keys)
 def test_reorder_and_decimal_format_are_equal(self):
  self.assertEqual(self.diff('period,pl\na,10.00\nb,20\n','period,pl\nb,20.0\na,10\n'),[])
 def test_offsets_do_not_hide_at_total(self):
  self.assertTrue(self.diff('period,pl\na,10\nb,20\n','period,pl\na,11\nb,19\n'))
 def test_null_is_not_zero(self):
  self.assertTrue(self.diff('period,pl\na,\n','period,pl\na,0\n'))
 def test_missing_group_is_not_ignored(self):
  self.assertTrue(self.diff('period,pl\na,10\nb,20\n','period,pl\na,10\n'))
 def test_duplicate_group_is_rejected(self):
  with self.assertRaises(ValueError):self.diff('period,pl\na,10\na,10\n','period,pl\na,20\n')
 def test_nan_and_empty_are_rejected(self):
  for s in ['period,pl\na,NaN\n','period,pl\n']:
   with self.assertRaises(ValueError):self.diff(s,s)
 def test_removed_metric_is_rejected(self):
  self.assertTrue(self.diff('period,pl,flow\na,10,2\n','period,pl\na,10\n'))
class Gate(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.tmp.name)
  for rid in ('a','b','c'):
   p=self.root/('work-'+rid);p.mkdir();(p/'snapshot.duckdb').write_bytes(rid.encode())
   (p/'validation.json').write_text(json.dumps({'passed':True,'source_hashes':{k:'frozen' for k in uat.INPUTS}}))
   seal(self.root,p,rid)
 def tearDown(self):self.tmp.cleanup()
 def tables(self,*args):
  return {name:','.join([*spec['keys'],*spec['metrics'].split(',')])+'\n'+','.join(['group']*len(spec['keys'])+['10']*len(spec['metrics'].split(',')))+'\n' for name,spec in uat.QUERIES.items()}
 def evaluate(self,base,candidate,bootstrap=False):
  with patch.object(uat,'collect',side_effect=self.tables):return uat.evaluate(self.root,base,candidate,bootstrap=bootstrap)
 def boot(self):
  gate=self.evaluate('a','a',True);promote(self.root,'uat','a',gate=gate)
 def test_uat_without_gate_is_blocked(self):
  with self.assertRaises(ValueError):promote(self.root,'uat','a')
 def test_equal_gate_allows_promotion(self):
  self.boot();gate=self.evaluate('a','b');promote(self.root,'uat','b','a',gate=gate)
  self.assertEqual(resolve(self.root,'uat').name,'b')
 def test_wrong_candidate_gate_blocks(self):
  self.boot();gate=self.evaluate('a','b')
  with self.assertRaises(ValueError):promote(self.root,'uat','c','a',gate=gate)
  self.assertEqual(resolve(self.root,'uat').name,'a')
 def test_stale_baseline_blocks(self):
  self.boot();ab=self.evaluate('a','b');ac=self.evaluate('a','c');promote(self.root,'uat','c','a',gate=ac)
  with self.assertRaises(ValueError):promote(self.root,'uat','b','c',gate=ab)
 def test_unequal_gate_preserves_baseline(self):
  self.boot()
  def changed(bundle):
   result=self.tables()
   if bundle.name=='b':result['total']=result['total'].replace('10','11')
   return result
  with patch.object(uat,'collect',side_effect=changed):gate=uat.evaluate(self.root,'a','b')
  with self.assertRaises(ValueError):promote(self.root,'uat','b','a',gate=gate)
  self.assertEqual(resolve(self.root,'uat').name,'a')
 def test_editing_pass_flag_cannot_hide_metric_difference(self):
  self.boot()
  def changed(bundle):
   result=self.tables()
   if bundle.name=='b':result['total']=result['total'].replace('10','11')
   return result
  with patch.object(uat,'collect',side_effect=changed):gate=uat.evaluate(self.root,'a','b')
  report=json.loads(gate.read_text());report['passed']=True;report['differences']={};gate.write_text(json.dumps(report))
  with self.assertRaises(ValueError):promote(self.root,'uat','b','a',gate=gate)
 def test_modified_inputs_refuse_comparison(self):
  p=self.root/'work-d';p.mkdir();(p/'snapshot.duckdb').write_bytes(b'd')
  (p/'validation.json').write_text(json.dumps({'passed':True,'source_hashes':{k:'new' for k in uat.INPUTS}}));seal(self.root,p,'d')
  with self.assertRaises(ValueError):self.evaluate('a','d')
 def test_incomplete_probe_report_is_rejected(self):
  self.boot();gate=self.evaluate('a','b');r=json.loads(gate.read_text());r['baseline_results'].pop('total');gate.write_text(json.dumps(r))
  with self.assertRaises(ValueError):promote(self.root,'uat','b','a',gate=gate)

class RequiredMetrics(unittest.TestCase):
 def test_same_missing_metric_on_both_sides_blocks(self):
  tables={name:','.join([*s['keys'],'unknown'])+'\n'+','.join(['group']*len(s['keys'])+['10'])+'\n' for name,s in uat.QUERIES.items()}
  with self.assertRaises(ValueError):uat.differences(tables,tables)
