"""Pinned Linux documentation driver; downloads only during explicit image bootstrap."""
import argparse,ctypes,ctypes.util,hashlib,json,os,platform,subprocess,tempfile,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];COMPAT=ROOT/'compatibility/dbt-v2-metricflow'
def verify_driver(path,lock):
    if not path.is_file():raise ValueError('Pinned Linux driver missing')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    if path.stat().st_size!=lock['size'] or digest!=lock['sha256']:raise ValueError('Driver checksum mismatch')
    return digest

def main():
    p=argparse.ArgumentParser();p.add_argument('--bootstrap',action='store_true');p.add_argument('--project',type=Path);a=p.parse_args()
    lock=json.loads((ROOT/'ci/docs-driver-linux.lock.json').read_text())
    if not a.bootstrap and platform.system()+'-'+platform.machine()!=lock['platform']:raise ValueError('Unvalidated docs platform')
    dbt=COMPAT/'.venv-dbt/bin/dbt';py=COMPAT/'.venv-mf/bin/python'
    env={**os.environ,'DBT_SEND_ANONYMOUS_USAGE_STATS':'false'}
    if not a.bootstrap and subprocess.check_output([str(dbt),'--version'],text=True).strip()!='dbt '+lock['dbt_version']:raise ValueError('Wrong dbt version')
    dest=ROOT/'ci/drivers';dest.mkdir(exist_ok=True);driver=dest/lock['filename']
    def run(args,project):subprocess.run([str(x) for x in args],cwd=project,env=env,check=True,timeout=240)
    if a.bootstrap:prepare(lock,dest)
    digest=verify_driver(driver,lock)
    (dest/'duckdb.toml').write_text('manifest_version = 1\nname = "Pinned Linux docs driver"\nversion = '+json.dumps(lock['driver_version'])+'\n[Driver]\nentrypoint = "duckdb_adbc_init"\nshared = '+json.dumps(str(driver))+'\n')
    if a.bootstrap:return
    if a.project is None:p.error('--project is required')
    project=a.project.resolve();env['ADBC_DRIVER_PATH']=str(dest);env['CVM_TARGET']='dev';env['CVM_DB_PATH']=str(project.parent/'snapshot.duckdb')
    manifest=project/'target/manifest.json';before=hashlib.sha256(manifest.read_bytes()).hexdigest()
    run([dbt,'docs','generate','--no-compile','--profiles-dir',project,'--target','dev'],project)
    if before!=hashlib.sha256(manifest.read_bytes()).hexdigest():raise ValueError('Docs changed build manifest')
    models=verify_documentation(project/'target')
    print(json.dumps({'driver_sha256':digest,'manifest_sha256':before,'documented_models':models}))




def verify_documentation(target):
    import duckdb
    target=Path(target)
    html=target/'index.html'
    if not html.is_file() or '<html' not in html.read_text().lower() and '<!doctype html>' not in html.read_text().lower():raise ValueError('Generated docs HTML missing')
    with duckdb.connect() as connection:
        count=connection.execute('select count(*) from read_parquet(?)',[str(target/'info_schema/v1/dbt.models.parquet')]).fetchone()[0]
    if not count:raise ValueError('Empty documentation models')
    return count

def prepare(lock,dest):
    dest=Path(dest);dest.mkdir(parents=True,exist_ok=True);driver=dest/lock['filename']
    if driver.exists():return verify_driver(driver,lock)
    if not 0<lock['size']<=150_000_000 or not 0<lock['compressed_size']<=100_000_000:raise ValueError('Driver exceeds bounded size')
    with urllib.request.urlopen(lock['url'],timeout=120) as response:packed=response.read(lock['compressed_size']+1)
    if len(packed)!=lock['compressed_size'] or hashlib.sha256(packed).hexdigest()!=lock['compressed_sha256']:raise ValueError('Compressed driver checksum mismatch')
    library=ctypes.util.find_library('zstd')
    if library is None:raise ValueError('System libzstd is required for bootstrap')
    zstd=ctypes.CDLL(library);zstd.ZSTD_decompress.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p,ctypes.c_size_t];zstd.ZSTD_decompress.restype=ctypes.c_size_t
    output=ctypes.create_string_buffer(lock['size']);source=ctypes.create_string_buffer(packed)
    length=zstd.ZSTD_decompress(output,lock['size'],source,len(packed))
    if length!=lock['size'] or hashlib.sha256(output.raw).hexdigest()!=lock['sha256']:raise ValueError('Unpacked driver checksum mismatch')
    fd,temp=tempfile.mkstemp(dir=dest)
    try:
        with os.fdopen(fd,'wb') as f:f.write(output.raw);f.flush();os.fsync(f.fileno())
        os.replace(temp,driver)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    return verify_driver(driver,lock)

if __name__=='__main__':main()
