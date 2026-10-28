"""Load the pinned official CVM archives into immutable landing + JSON envelopes."""
from pathlib import Path
import sys,csv,hashlib,json,os
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ingestion.cvm import land,envelopes
from ingestion.store import register
import duckdb
ROOT=Path(__file__).resolve().parents[1]
def main():
    p=ROOT/'profiling/cvm';objects=ROOT/'data/landing/objects'
    manifest=json.loads((p/'evidence/sources.json').read_text())
    cohort_bytes=(p/'evidence/cohort.csv').read_bytes();calendar_bytes=(p/'evidence/calendar.json').read_bytes()
    cohort=list(csv.DictReader(cohort_bytes.decode().splitlines()));calendar=json.loads(calendar_bytes)
    keys={r['cnpj'] for r in cohort}
    if len(keys)!=60 or len(cohort)!=60:raise ValueError('Unexpected frozen population')
    capture=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    signature=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()+cohort_bytes+calendar_bytes).hexdigest()
    land(cohort_bytes,objects);land(calendar_bytes,objects);land(json.dumps(manifest,sort_keys=True).encode(),objects)
    observations=[];files=[]
    for entry in manifest:
        data=(p/entry['file']).read_bytes()
        if hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Source hash mismatch: '+entry['file'])
        land(data,objects)
        if not Path(entry['file']).name.startswith('inf_diario_fi_'):continue
        rows,excluded=envelopes(data,keys)
        for r in rows:
            source=f"{entry['sha256']}:{r['member']}:{r['line_start']}"
            observations.append((capture,source,r['period'],r['payload']))
        # Member name is deterministic even when no row is selected.
        member=Path(entry['file']).stem+'.csv'
        files.append((capture,entry['sha256'],member,len(rows),excluded))
    db=os.environ.get('CVM_DB_PATH',str(ROOT/'transform/cvm_demo.duckdb'))
    with duckdb.connect(db,config={'storage_compatibility_version':'v1.4.0'}) as c:
        inserted=register(c,capture,max(r['observed_at'] for r in manifest),signature,observations,
            [(r['cnpj'],'CVM:CLASS:'+r['ID_Registro_Classe'],r['Classificacao']) for r in cohort],
            [(r['date'],) for r in calendar],files)
    print(json.dumps({'capture_id':capture,'inserted':inserted,'enveloped':len(observations),'excluded':sum(r[4] for r in files),'files':len(files)}))
if __name__=='__main__':main()
