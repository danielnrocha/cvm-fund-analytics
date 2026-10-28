"""Online setup only: fetch exact frozen bytes, never refresh the source manifest."""
import hashlib,json,os,tempfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def fetch(manifest,root):
    root=Path(root).resolve()
    for entry in manifest:
        path=(root/entry['file']).resolve()
        if not path.is_relative_to(root):raise ValueError('Source path escapes root')
        if path.exists():data=path.read_bytes()
        else:
            with urllib.request.urlopen(entry['url'],timeout=180) as response:data=response.read(entry['bytes']+1)
        if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Frozen source drift: '+entry['file'])
        if not path.exists():
            path.parent.mkdir(parents=True,exist_ok=True)
            fd,tmp=tempfile.mkstemp(dir=path.parent)
            try:
                with os.fdopen(fd,'wb') as f:f.write(data)
                os.replace(tmp,path)
            finally:
                if os.path.exists(tmp):os.unlink(tmp)
if __name__=='__main__':fetch(json.loads((ROOT/'profiling/cvm/evidence/sources.json').read_text()),ROOT/'profiling/cvm')
