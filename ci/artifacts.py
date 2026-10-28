"""Artifact acceptance: prove lineage for stock, both cashflow inputs and JSON extraction."""
import duckdb

def check_lineage(path):
    required={('model.cvm_demo.current_daily','pl','model.cvm_demo.fct_daily','pl'),
              ('model.cvm_demo.current_daily','subscriptions','model.cvm_demo.fct_daily','net_flow'),
              ('model.cvm_demo.current_daily','redemptions','model.cvm_demo.fct_daily','net_flow'),
              ('source.cvm_demo.cvm_landing.raw_envelopes','payload','model.cvm_demo.bronze_classified','pl')}
    with duckdb.connect() as c:
        edges=set(c.execute('select parent_node_unique_id,parent_column_name,child_node_unique_id,child_column_name from read_parquet(?)',[str(path)]).fetchall())
    if not required<=edges:raise ValueError('Missing required column lineage: '+repr(required-edges))
    return len(required)
