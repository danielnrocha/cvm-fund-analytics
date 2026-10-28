"""Local single-host bundle publication. Filesystem owner remains trusted."""
import contextlib,fcntl,hashlib,json,os,pathlib,re,shutil,tempfile

def _name(value):
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}',value):raise ValueError('Invalid release id')
    return value

def _environment(value):
    if value not in ('dev','uat'):raise ValueError('Environment must be dev or uat')
    return value

@contextlib.contextmanager
def _lock(root):
    root=pathlib.Path(root);_mkdir(root)
    with (root/'.publication.lock').open('a') as f:
        fcntl.flock(f,fcntl.LOCK_EX)
        yield root

def _sync(path):
    fd=os.open(path,os.O_RDONLY)
    try:os.fsync(fd)
    finally:os.close(fd)

def _mkdir(path):
    path=pathlib.Path(path)
    if path.exists():return
    _mkdir(path.parent)
    try:path.mkdir()
    except FileExistsError:pass
    _sync(path.parent)

def _hashes(path):
    result={}
    for p in sorted(path.rglob('*')):
        if p.is_symlink():raise ValueError('Symlinks are not bundle content')
        if p.is_file() and p.relative_to(path).as_posix()!='bundle.json':result[str(p.relative_to(path))]=hashlib.sha256(p.read_bytes()).hexdigest()
    return result

def _verify(root,release_id):
    path=pathlib.Path(root)/'snapshots'/_name(release_id)
    if path.is_symlink():raise ValueError('Symlink bundle forbidden')
    manifest=json.loads((path/'bundle.json').read_text())
    if manifest['release_id']!=release_id or manifest['files']!=_hashes(path):raise ValueError('Bundle checksum mismatch')
    if json.loads((path/'validation.json').read_text()).get('passed') is not True:raise ValueError('Candidate not validated')
    return path

def seal(root,candidate,release_id):
    _name(release_id);candidate=pathlib.Path(candidate)
    if json.loads((candidate/'validation.json').read_text()).get('passed') is not True:raise ValueError('Candidate validation failed')
    if not (candidate/'snapshot.duckdb').is_file() or list(candidate.glob('*.wal')):raise ValueError('Closed database required')
    _hashes(candidate) # Reject links before copying.
    with _lock(root) as root:
        parent=root/'snapshots';_mkdir(parent)
        target=parent/release_id
        if target.exists():raise ValueError('Release already exists')
        staging=pathlib.Path(tempfile.mkdtemp(prefix='.sealing-',dir=parent))
        try:
            shutil.copytree(candidate,staging,dirs_exist_ok=True)
            manifest={'release_id':release_id,'files':_hashes(staging)}
            (staging/'bundle.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
            for p in staging.rglob('*'):
                if p.is_file():_sync(p);p.chmod(0o444)
            for directory in sorted((p for p in staging.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):_sync(directory)
            _sync(staging);os.rename(staging,target);_sync(parent)
        except BaseException:
            shutil.rmtree(staging,ignore_errors=True);raise
    return _verify(root,release_id)

def _state(root,environment):
    p=root/'environments'/_environment(environment)/'current.json'
    return json.loads(p.read_text()) if p.exists() else {'release_id':None,'history':[]}

def _write(root,environment,state):
    directory=root/'environments'/environment;_mkdir(directory)
    fd,temp=tempfile.mkstemp(prefix='.pointer-',dir=directory)
    try:
        with os.fdopen(fd,'w') as f:json.dump(state,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
        os.replace(temp,directory/'current.json');_sync(directory)
    finally:
        if os.path.exists(temp):os.unlink(temp)

def promote(root,environment,release_id,expected=None,gate=None):
    _environment(environment)
    with _lock(root) as root:
        _verify(root,release_id);old=_state(root,environment)
        if old['release_id']!=expected:raise ValueError('Stale environment pointer')
        gate_hash=None
        if environment=='uat':
            from release.uat import verify_gate
            gate_hash=verify_gate(root,gate,expected,release_id)
        if expected==release_id:return
        history=old['history']+([expected] if expected else [])
        _write(root,environment,{'release_id':release_id,'history':history,'action':'promote','gate_sha256':gate_hash})

def resolve(root,environment):
    # Read pointer exactly once. Its immutable path is pinned for the caller's whole query.
    root=pathlib.Path(root);release_id=_state(root,environment)['release_id']
    if release_id is None:raise ValueError('Environment is not published')
    return _verify(root,release_id)

def rollback(root,environment,expected=None):
    _environment(environment)
    with _lock(root) as root:
        old=_state(root,environment)
        if old['release_id']!=expected or not old['history']:raise ValueError('Stale pointer or no rollback target')
        target=old['history'][-1];_verify(root,target)
        _write(root,environment,{'release_id':target,'history':old['history'][:-1],'action':'rollback'})
