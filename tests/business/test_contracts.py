"""Literal oracles: duplicate inflation, identity collapse, missing=0, unsafe joins."""
import copy,json,pathlib,unittest
from decimal import Decimal as D
import probe
P=pathlib.Path(__file__).parent
class Contracts(unittest.TestCase):
 def setUp(self):
  self.raw=json.loads((P/'fixtures/observations.json').read_text())
  self.registry=[{'kind':'CLASS','cnpj':'00000000000100','subclass':None,'entity':'CVM:CLASS:A'}, {'kind':'CLASS','cnpj':'00000000000200','subclass':None,'entity':'CVM:CLASS:B'}]
  self.facts=[{'entity':'A','date':'2026-04-01','pl':D('100'),'flow':D('10')},{'entity':'B','date':'2026-04-01','pl':D('200'),'flow':D('20')},{'entity':'A','date':'2026-04-02','pl':D('110'),'flow':D('0')}]
 def test_duplicate_keeps_all_sources_without_inflating_values(self):
  actual=probe.deduplicate(self.raw)
  self.assertEqual(len(actual),3)
  self.assertEqual(sum(D(r['pl']) for r in actual),D('410'))
  self.assertEqual(actual[0]['sources'],['file1:2','file1:3'])
  self.assertEqual(len(self.raw),4)
 def test_conflicting_same_capture_blocks_even_if_pl_equal(self):
  self.raw[1]['flow']='11.00'
  with self.assertRaises(ValueError):probe.deduplicate(self.raw)
 def test_capture_sequence_a_b_a_keeps_versions(self):
  a=self.raw[0];b=dict(a,capture='v2',source='file2:2',pl='105.00');again=dict(a,capture='v3',source='file3:2')
  try: actual=probe.deduplicate([a,b,again,a])
  except ValueError as exc:self.fail(f'Valid capture history rejected: {exc}')
  self.assertEqual([r['pl'] for r in actual],['100.00','105.00','100.00'])
 def test_namespace_and_parent_scope_prevent_identity_collapse(self):
  reg=[dict(self.registry[0],kind='FUND',entity='CVM:FUND:A'),*self.registry,dict(self.registry[0],subclass='X',entity='CVM:CLASS:A:SUB:X'),dict(self.registry[1],subclass='X',entity='CVM:CLASS:B:SUB:X')]
  data=[dict(self.raw[0],kind='FUND'),self.raw[0],dict(self.raw[0],subclass='X'),dict(self.raw[2],subclass='X')]
  try: actual=probe.resolve(data,reg)
  except ValueError as exc:self.fail(f'Valid hierarchical identities rejected: {exc}')
  self.assertEqual([r['entity'] for r in actual],['CVM:FUND:A','CVM:CLASS:A','CVM:CLASS:A:SUB:X','CVM:CLASS:B:SUB:X'])
 def test_unknown_or_ambiguous_identity_blocks(self):
  for registry in [[],self.registry+[dict(self.registry[0],entity='CVM:CLASS:OTHER')]]:
   with self.subTest(registry=registry),self.assertRaises(ValueError):probe.resolve([self.raw[0]],registry)
 def test_invalid_cnpj_not_silently_repaired(self):
  with self.assertRaises(ValueError):probe.resolve([dict(self.raw[0],cnpj='garbage00000000000100')],self.registry)
 def test_dimension_join_preserves_rows_and_sum(self):
  out=probe.enrich(self.facts,[{'entity':'A','category':'RF'},{'entity':'B','category':'MM'}])
  self.assertEqual(len(out),3);self.assertEqual(sum(r['pl'] for r in out),D('410'))
 def test_ambiguous_and_missing_dimension_block_instead_of_dropping(self):
  for dim in [[{'entity':'A','category':'RF'}],[{'entity':'A','category':'RF'},{'entity':'A','category':'MM'},{'entity':'B','category':'MM'}]]:
   with self.subTest(dim=dim),self.assertRaises(ValueError):probe.enrich(self.facts,dim)
 def test_missing_cutoff_not_forward_filled_and_flow_is_partial(self):
  self.assertEqual(probe.summarize(self.facts,['A','B'],['2026-04-01','2026-04-02']),{'pl':D('110'),'flow':D('30'),'present':3,'expected':4,'cutoff_present':1,'cutoff_expected':2,'status':'partial'})
 def test_empty_cutoff_does_not_recede_to_previous_observation(self):
  out=probe.summarize(self.facts,['A','B'],['2026-04-01','2026-04-02','2026-04-03'])
  self.assertIsNotNone(out)
  self.assertIsNone(out['pl']);self.assertEqual(out['cutoff_present'],0)
 def test_empty_population_is_no_data_not_certified_zero(self):
  self.assertEqual(probe.summarize(self.facts,[],['2026-04-01']),{'pl':None,'flow':None,'present':0,'expected':0,'cutoff_present':0,'cutoff_expected':0,'status':'no_data'})
 def test_duplicate_fact_blocks_coverage_above_one(self):
  with self.assertRaises(ValueError):probe.summarize(self.facts+[self.facts[0]],['A','B'],['2026-04-01','2026-04-02'])
 def test_derived_flow_preserves_difference_of_two_source_decimals(self):
  # 999999999999999.99 - (-999999999999999.99), both DECIMAL(17,2).
  fact=dict(self.facts[0],flow=D('1999999999999999.98'))
  try: actual=probe.summarize([fact],['A'],['2026-04-01'])
  except Exception as exc:self.fail(f'Valid derived monetary amount rejected: {exc}')
  self.assertEqual(actual['flow'],D('1999999999999999.98'))
if __name__=='__main__':unittest.main()
