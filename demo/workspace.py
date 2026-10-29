"""Disposable teaching workspace. No downloads, Docker, or environment promotion."""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
MARKER = '.cvm-demo.json'

def location(root):
    root = Path(root).resolve()
    work = root / 'data/demo'
    if (root / 'data').is_symlink() or work.is_symlink():
        raise ValueError('Demo workspace and parent must not be symlinks')
    return work

def owned(root):
    work = location(root)
    if not work.is_dir() or any(p.is_symlink() for p in work.rglob('*')):
        raise ValueError('Missing workspace or symlink inside workspace')
    marker = work / MARKER
    if not marker.is_file() or json.loads(marker.read_text()) != {'owner': 'cvm-live-demo-v1', 'root': str(Path(root).resolve())}:
        raise ValueError('Refusing to modify an unowned demo directory')
    return work

def validate_sources(root, database):
    database = Path(database)
    if not database.is_file() or database.is_symlink() or Path(str(database) + '.wal').exists():
        raise ValueError('Source must be a closed, regular database without WAL')
    source = Path(root) / 'transform'
    if not source.is_dir() or source.is_symlink() or not (source / 'dbt_project.yml').is_file():
        raise ValueError('Source dbt project is unavailable')
    if any(p.is_symlink() for p in source.rglob('*')):
        raise ValueError('Source project must not contain symlinks')
    return source

def prepare(root, database):
    root = Path(root).resolve()
    work = location(root)
    source = validate_sources(root, database)
    if work.exists():
        raise FileExistsError('Demo already exists; use explicit reset')
    work.mkdir(parents=True)
    # Marker is written last: partial setup cannot be silently deleted by reset.
    shutil.copytree(source, work / 'project', ignore=shutil.ignore_patterns('target', 'logs', 'evidence', '*.duckdb*', '__pycache__', 'seeds'))
    shutil.copyfile(database, work / 'demo.duckdb')
    project = work / 'project'
    (project / 'evidence').mkdir()
    (project / 'profiles.yml').write_text('cvm_demo:\n  target: dev\n  outputs:\n    dev:\n      type: duckdb\n      path: ' + json.dumps(str(work / 'demo.duckdb')) + '\n      schema: main\n      threads: 1\n')
    tools = root / 'compatibility/dbt-v2-metricflow'
    env = {'DEMO_ROOT': str(root), 'DEMO_PROJECT': str(project), 'DBT': str(tools / '.venv-dbt/bin/dbt'), 'MF': str(tools / '.venv-mf/bin/mf'), 'PY': str(tools / '.venv-mf/bin/python'), 'DBT_PROJECT_DIR': str(project), 'DBT_TARGET': 'dev', 'DBT_TARGET_PATH': str(project / 'target'), 'DBT_LOG_PATH': str(project / 'logs'), 'DBT_PROFILES_DIR': str(project), 'CVM_PROJECT_DIR': str(project), 'CVM_DB_PATH': str(work / 'demo.duckdb'), 'CVM_TARGET': 'dev', 'DBT_SEND_ANONYMOUS_USAGE_STATS': 'false'}
    (work / 'env.sh').write_text('\n'.join('export ' + k + '=' + shlex.quote(v) for k, v in env.items()) + '\nunset PYTHONOPTIMIZE\ncd "$DEMO_PROJECT"\n')
    workspace = {
        'folders': [{'path': 'project'}],
        'settings': {
            'dbt.targetName': 'dev',
            'dbt.flag.defer': False,
            'dbt.formatOnSave': True,
            'dbt.lintFixOnSave': False,
            'editor.insertSpaces': True,
            'editor.detectIndentation': False,
            'editor.tabSize': 4,
            '[yaml]': {'editor.tabSize': 2},
            '[json]': {'editor.tabSize': 2},
        },
        'extensions': {'recommendations': ['dbtLabsInc.dbt']},
    }
    (work / 'official-dbt.code-workspace').write_text(
        json.dumps(workspace, indent=2) + '\n')
    (work / MARKER).write_text(json.dumps({'owner': 'cvm-live-demo-v1', 'root': str(root)}))
    return work

def reset(root, database):
    work = owned(root)
    # Verify prerequisite before deleting the previous exercise.
    validate_sources(Path(root).resolve(), database)
    shutil.rmtree(work)
    return prepare(root, database)

def baseline():
    sys.path.insert(0, str(ROOT))
    from release.snapshots import _verify
    lock = json.loads((ROOT / 'ci/baseline.lock.json').read_text())
    return _verify(ROOT / 'baseline/releases', lock['release_id']) / 'snapshot.duckdb'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['prepare', 'reset'])
    args = parser.parse_args()
    database = baseline()  # Local verification only; missing baseline is an error.
    work = prepare(ROOT, database) if args.action == 'prepare' else reset(ROOT, database)
    print('Workspace ready. In a dedicated terminal: source ' + shlex.quote(str(work / 'env.sh')))

if __name__ == '__main__':
    main()
