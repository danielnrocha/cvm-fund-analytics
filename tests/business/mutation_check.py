"""Run realistic defects against the unchanged tests in disposable directories."""
import json,pathlib,shutil,subprocess,sys,tempfile
P=pathlib.Path(__file__).resolve().parent
source=(P/'probe.py').read_text()
mutations={
 'duplicate_inflation':("key = (row['capture'], identity(row), row['date'])", "key = (row['capture'], identity(row), row['date'], row['source'])"),
 'erase_capture_history':("key = (row['capture'], identity(row), row['date'])", "key = (identity(row), row['date'])"),
 'collapse_subclass_scope':("return row['kind'], re.sub(r'[^0-9]', '', cnpj), sub", "return row['kind'], re.sub(r'[^0-9]', '', cnpj), None"),
 'arbitrary_dimension_match':("if len(matches) != 1:\n            raise ValueError('Dimension join requires exactly one match')", "if len(matches) == 0:\n            raise ValueError('Dimension join requires exactly one match')"),
 'recede_cutoff':("cutoff = max(dates) if dates else None", "cutoff = max((r['date'] for r in selected), default=None)"),
 'missing_equals_zero':("sum(pl) filter(where day = cast(? as date)), sum(flow)", "coalesce(sum(pl) filter(where day = cast(? as date)), 0), coalesce(sum(flow), 0)")
}
results=[]
for name,(old,new) in mutations.items():
 assert source.count(old)==1, name
 with tempfile.TemporaryDirectory(prefix='cvm-mutation-') as tmp:
  root=pathlib.Path(tmp);shutil.copytree(P/'fixtures',root/'fixtures')
  shutil.copy(P/'test_contracts.py',root/'test_contracts.py')
  (root/'probe.py').write_text(source.replace(old,new))
  run=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(root),'-v'],capture_output=True,text=True)
  (P/'evidence'/f'mutation-{name}.log').write_text(run.stdout+run.stderr)
  # Assertion failures, not merely crashes/import errors, must expose the defect.
  detected=run.returncode!=0 and 'FAIL:' in run.stderr
  results.append({'mutation':name,'returncode':run.returncode,'assertion_detected':detected})
(P/'evidence/mutations.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2));assert all(r['assertion_detected'] for r in results)
