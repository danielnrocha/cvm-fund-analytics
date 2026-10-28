import sys,pathlib,unittest,tempfile,zipfile,io,json,hashlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from ingestion.cvm import land,envelopes
HEADER='TP_FUNDO_CLASSE;CNPJ_FUNDO_CLASSE;ID_SUBCLASSE;DT_COMPTC;VL_TOTAL;VL_QUOTA;VL_PATRIM_LIQ;CAPTC_DIA;RESG_DIA;NR_COTST\n'
ROW='CLASSES - FIF;00.000.000/0001-00;;2026-04-01;100.00;1.000000000000;100.00;10.00;0.00;2\n'
def archive(text,name='inf_diario_fi_202604.csv'):
 b=io.BytesIO()
 with zipfile.ZipFile(b,'w') as z:z.writestr(name,text.encode('latin1'))
 return b.getvalue()
class Ingestion(unittest.TestCase):
 def test_landing_retains_exact_bytes_and_replay_path(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=archive(HEADER+ROW);p=land(data,pathlib.Path(tmp))
   self.assertIsNotNone(p);self.assertEqual(p.read_bytes(),data)
   self.assertEqual(land(data,pathlib.Path(tmp)),p)
 def test_corrupted_existing_object_is_never_repaired_silently(self):
  with tempfile.TemporaryDirectory() as tmp:
   data=b'original';p=pathlib.Path(tmp)/hashlib.sha256(data).hexdigest();p.write_bytes(b'corrupted')
   with self.assertRaises(ValueError):land(data,pathlib.Path(tmp))
 def test_envelope_preserves_strings_null_and_extra_field(self):
  rows,excluded=envelopes(archive(HEADER.rstrip()+';NEW\n'+ROW.rstrip()+';value\n'),{'00000000000100'})
  self.assertEqual(len(rows),1);self.assertEqual(excluded,0)
  row=json.loads(rows[0]['payload']);self.assertEqual(row['data']['VL_QUOTA'],'1.000000000000')
  self.assertEqual(row['data']['ID_SUBCLASSE'],None);self.assertEqual(row['data']['NEW'],'value')
  self.assertEqual(rows[0]['record_number'],1)
  self.assertEqual(row['error'],'unknown_columns')
 def test_out_of_cohort_is_counted_not_lost(self):
  rows,excluded=envelopes(archive(HEADER+ROW+ROW.replace('0001-00','0002-00')),{'00000000000100'})
  self.assertEqual((len(rows),excluded),(1,1))
 def test_missing_required_header_blocks_file(self):
  with self.assertRaises(ValueError):envelopes(archive(HEADER.replace('VL_QUOTA','WRONG')+ROW),{'00000000000100'})
 def test_malformed_row_is_preserved_for_quarantine(self):
  rows,excluded=envelopes(archive(HEADER+ROW.rstrip()+';EXTRA\n'),{'00000000000100'})
  self.assertEqual(len(rows),1);self.assertEqual(json.loads(rows[0]['payload'])['error'],'csv_width')
 def test_invalid_identifier_cannot_disappear_as_excluded(self):
  rows,excluded=envelopes(archive(HEADER+ROW.replace('00.000.000/0001-00','BAD')),{'00000000000100'})
  self.assertEqual((len(rows),excluded),(1,0))
  self.assertEqual(json.loads(rows[0]['payload'])['error'],'invalid_cnpj')
 def test_zip_path_and_truncated_archive_fail(self):
  for data in [archive(HEADER+ROW,'../escape.csv'),b'bad zip']:
   with self.subTest(data=data[:8]),self.assertRaises(ValueError):envelopes(data,{'00000000000100'})
 def test_multiline_csv_tracks_physical_start_and_end(self):
  text=HEADER.rstrip()+';NEW\n'+ROW.rstrip()+';"first\nsecond"\n'+ROW.rstrip()+';plain\n'
  rows,_=envelopes(archive(text),{'00000000000100'})
  self.assertIn('line_start',rows[0])
  self.assertEqual([(r['line_start'],r['line_end']) for r in rows],[(2,3),(4,4)])
if __name__=='__main__':unittest.main()
