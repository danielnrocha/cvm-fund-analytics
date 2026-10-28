"""Bounded research download; not a production ingestion pipeline."""
import concurrent.futures, datetime, hashlib, json, pathlib, urllib.request, zipfile
ROOT = pathlib.Path(__file__).resolve().parent
manifest_path=ROOT/'evidence'/'sources.json'
previous={r['url']:r for r in json.loads(manifest_path.read_text())} if manifest_path.exists() else {}
urls = ['https://dados.cvm.gov.br/dados/FI/CAD/DADOS/registro_fundo_classe.zip', 'https://dados.cvm.gov.br/dados/FI/CAD/META/meta_registro_fundo_classe.zip', 'https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/META/meta_inf_diario_fi.txt'] + [f'https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS/inf_diario_fi_2026{m:02}.zip' for m in range(4,10)]
def fetch(url):
    path = ROOT/'raw'/url.rsplit('/',1)[1]
    if not path.exists():
        with urllib.request.urlopen(url, timeout=180) as r:
            data = r.read(150_000_001)
        if len(data)>150_000_000: raise ValueError('Download exceeds research limit')
        path.write_bytes(data)
    data=path.read_bytes()
    if url in previous:
        if hashlib.sha256(data).hexdigest()!=previous[url]['sha256']: raise ValueError('Source changed: keep frozen snapshot; create a new capture explicitly')
    if path.suffix=='.zip':
        dest=ROOT/'extracted'/path.stem; dest.mkdir(exist_ok=True)
        with zipfile.ZipFile(path) as z:
            if sum(i.file_size for i in z.infolist())>1_000_000_000: raise ValueError('Archive too large')
            for name in z.namelist():
                if pathlib.Path(name).name != name: raise ValueError('Unexpected archive path')
            z.extractall(dest)
    if url in previous: return previous[url]
    return dict(url=url,file=str(path.relative_to(ROOT)),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    records=list(pool.map(fetch,urls))
(ROOT/'evidence'/'sources.json').write_text(json.dumps(records,indent=2)+'\n')
for row in records: print(row['file'],row['bytes'])
