"""Pinned Release assets, independent of ephemeral Actions artifact retention."""
import argparse,hashlib,json,os,re,shutil,stat,sys,tempfile,urllib.request,zipfile
from pathlib import Path,PurePosixPath
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from release.snapshots import _verify,_name
MAX_ARCHIVE=100_000_000
MAX_UNPACKED=256_000_000

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def pack(root,release_id,archive,tag):
    bundle=_verify(root,release_id);_name(tag)
    archive=Path(archive);archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(bundle.rglob('*')):
            if path.is_file():
                name='snapshots/'+release_id+'/'+path.relative_to(bundle).as_posix()
                entry=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0))
                entry.external_attr=(stat.S_IFREG|0o444)<<16
                output.writestr(entry,path.read_bytes(),compress_type=zipfile.ZIP_DEFLATED)
    _verify(root,release_id)
    return {'version':1,'tag':tag,'asset':archive.name,'release_id':release_id,'size':archive.stat().st_size,'sha256':digest(archive)}

def restore(archive,lock,destination):
    archive=Path(archive);destination=Path(destination)
    _name(lock['release_id'])
    if destination.exists():raise FileExistsError(destination)
    if lock['version']!=1 or not 0<lock['size']<=MAX_ARCHIVE or archive.stat().st_size!=lock['size'] or digest(archive)!=lock['sha256']:
        raise ValueError('Baseline archive checksum/size mismatch')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        staging=Path(temporary)/'release';staging.mkdir()
        with zipfile.ZipFile(archive) as source:
            entries=source.infolist();names=[e.filename for e in entries]
            if len(entries)>10000 or len(names)!=len(set(names)) or sum(e.file_size for e in entries)>MAX_UNPACKED:
                raise ValueError('Invalid or oversized baseline archive')
            prefix='snapshots/'+lock['release_id']+'/'
            for entry in entries:
                name=entry.filename;parts=PurePosixPath(name).parts
                if not name.startswith(prefix) or any(p in ('.','..') for p in parts) or '\\' in name or str(PurePosixPath(name))!=name or stat.S_IFMT(entry.external_attr>>16) not in (0,stat.S_IFREG):
                    raise ValueError('Unsafe baseline archive member')
                target=staging/name;target.parent.mkdir(parents=True,exist_ok=True)
                with source.open(entry) as incoming,target.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing)
                target.chmod(0o444)
        _verify(staging,lock['release_id'])
        os.rename(staging,destination)
    return destination/'snapshots'/lock['release_id']

def fetch(lock,repository,destination):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):raise ValueError('Expected owner/repository')
    _name(lock['tag'])
    if not re.fullmatch(r'[A-Za-z0-9_-]+\.zip',lock['asset']):raise ValueError('Invalid asset name')
    if not 0<lock['size']<=MAX_ARCHIVE:raise ValueError('Oversized baseline')
    url=f"https://github.com/{repository}/releases/download/{lock['tag']}/{lock['asset']}"
    with tempfile.TemporaryDirectory() as temporary:
        archive=Path(temporary)/lock['asset']
        with urllib.request.urlopen(url,timeout=120) as response:
            archive.write_bytes(response.read(lock['size']+1))
        return restore(archive,lock,destination)

def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    make=sub.add_parser('pack');make.add_argument('--root',type=Path,required=True);make.add_argument('--id',required=True);make.add_argument('--archive',type=Path,required=True);make.add_argument('--tag',required=True);make.add_argument('--lock',type=Path,required=True)
    for action in ['restore','fetch']:
        command=sub.add_parser(action);command.add_argument('--lock',type=Path,default=Path('ci/baseline.lock.json'));command.add_argument('--destination',type=Path,default=Path('baseline/releases'))
        command.add_argument('--archive' if action=='restore' else '--repository',required=True)
    a=p.parse_args()
    if a.action=='pack':
        lock=pack(a.root,a.id,a.archive,a.tag);a.lock.write_text(json.dumps(lock,indent=2)+'\n');print(json.dumps(lock))
    elif a.action=='restore':print(restore(a.archive,json.loads(a.lock.read_text()),a.destination))
    else:print(fetch(json.loads(a.lock.read_text()),a.repository,a.destination))
if __name__=='__main__':main()
