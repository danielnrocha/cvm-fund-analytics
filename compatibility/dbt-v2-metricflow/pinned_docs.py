"""Use an exact documentation driver; fail closed rather than silently fetching another."""
import argparse, hashlib, json, os, platform, shutil, subprocess
from pathlib import Path
P=Path(__file__).resolve().parent

def verify(driver,lock):
    if not driver.is_file(): raise RuntimeError('Pinned driver missing; run pinned_docs.py --prepare after bootstrap')
    digest=hashlib.sha256(driver.read_bytes()).hexdigest()
    if digest!=lock['sha256'] or driver.stat().st_size!=lock['size']:
        raise RuntimeError('Pinned driver SHA-256/size mismatch; refusing fallback')
    return digest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--bootstrap',action='store_true');parser.add_argument('--verify-only',action='store_true');parser.add_argument('--driver-dir',type=Path,default=P/'drivers');args=parser.parse_args()
    lock=json.loads((P/'docs-driver.lock.json').read_text())
    if platform.system()+'-'+platform.machine()!=lock['platform']:raise RuntimeError('No verified driver lock for this platform')
    dbt=str(P/'.venv-dbt/bin/dbt');env=os.environ.copy();env['DBT_SEND_ANONYMOUS_USAGE_STATS']='false'
    version=subprocess.check_output([dbt,'--version'],text=True).strip()
    if version!='dbt '+lock['dbt_version']:raise RuntimeError('dbt version differs from driver lock')
    cache=Path.home()/'Library/Caches/com.getdbt/adbc/aarch64-apple-darwin'
    if args.bootstrap:
        # Explicit online setup only; subsequent verification must match the committed hash.
        subprocess.run([dbt,'compile','--profiles-dir','.', '--static-analysis','strict','--generate-info-schema'],cwd=P,env=env,check=True)
        subprocess.run([dbt,'docs','generate','--profiles-dir','.', '--no-compile'],cwd=P,env=env,check=True)
    dest=args.driver_dir.resolve();driver=dest/lock['filename']
    if args.prepare or args.bootstrap:
        source=cache/lock['filename'];verify(source,lock)
        dest.mkdir(parents=True,exist_ok=True);shutil.copy2(source,driver)
    digest=verify(driver,lock)
    if args.verify_only: print(json.dumps({'driver':str(driver),'sha256':digest,'verified':True}));return
    (dest/'duckdb.toml').write_text('manifest_version = 1\nname = "Pinned dbt docs driver"\nversion = '+json.dumps(lock['driver_version'])+'\n[Driver]\nentrypoint = "duckdb_adbc_init"\nshared = '+json.dumps(str(driver))+'\n')
    # Block both network and global cache: successful docs must use the checked local artifact.
    sandbox=P/'docs-driver-isolated.sb'
    sandbox.write_text('(version 1)\n(allow default)\n(deny network*)\n(deny file-read* (subpath '+json.dumps(str(cache.parent))+'))\n')
    env['ADBC_DRIVER_PATH']=str(dest)
    subprocess.run(['/usr/bin/sandbox-exec','-f',str(sandbox),dbt,'docs','generate','--no-compile','--profiles-dir','.'],cwd=P,env=env,check=True)
    print(json.dumps({'driver':str(driver),'sha256':digest,'network_and_global_cache_blocked':True}))
if __name__=='__main__':main()
