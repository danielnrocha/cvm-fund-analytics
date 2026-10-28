import pathlib,sys,tempfile,unittest
import duckdb
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]))
from ci.artifacts import check_lineage
class ColumnLineage(unittest.TestCase):
 def fixture(self,path,missing=False):
  rows=[('model.cvm_demo.current_daily','pl','model.cvm_demo.fct_daily','pl'),('model.cvm_demo.current_daily','subscriptions','model.cvm_demo.fct_daily','net_flow'),('model.cvm_demo.current_daily','redemptions','model.cvm_demo.fct_daily','net_flow'),('source.cvm_demo.cvm_landing.raw_envelopes','payload','model.cvm_demo.bronze_classified','pl')]
  if missing:rows.pop(2)
  with duckdb.connect() as c:
   c.execute('create table edges(parent_node_unique_id varchar,parent_column_name varchar,child_node_unique_id varchar,child_column_name varchar)');c.executemany('insert into edges values (?,?,?,?)',rows)
   c.execute('copy edges to ? (format parquet)',[str(path)])
 def test_missing_redemptions_lineage_blocks(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'edges.parquet';self.fixture(p,True)
   with self.assertRaises(ValueError):check_lineage(p)
 def test_cash_flow_and_json_lineage_pass(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d)/'edges.parquet';self.fixture(p)
   self.assertEqual(check_lineage(p),4)
