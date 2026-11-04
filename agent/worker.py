"""Worker process, scratch project, and installed MetricFlow runtime boundary."""
import json
import os
import signal
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import yaml

from agent.contracts import GatewayError

MAX_BYTES = 2 * 1024 * 1024
VERSIONS = {
    "dbt_core": "1.12.6",
    "dbt_duckdb": "1.11.1",
    "dbt_metricflow": "0.15.0",
    "duckdb": "2.0.0",
    "metricflow": "0.213.0",
}
ENTRY = Path(__file__).with_name("_mf_entry.py").resolve()
# Set file size limits before exec without using preexec_fn in a threaded host.
_LIMIT_EXEC = """
import os, resource, sys
size = int(sys.argv[1])
resource.setrlimit(resource.RLIMIT_FSIZE, (size, size))
os.execv(sys.argv[2], sys.argv[2:])
"""


def inspect_runtime(mf_executable: Path) -> dict[str, str]:
    if (not mf_executable.is_absolute() or mf_executable.name != "mf"
            or mf_executable.is_symlink() or not os.access(mf_executable, os.X_OK)):
        raise GatewayError("tool_error")
    site = mf_executable.parent.parent / "lib/python3.12/site-packages"
    for package, version in VERSIONS.items():
        found = [entry.name for entry in site.glob(f"{package}-*.dist-info")]
        if found != [f"{package}-{version}.dist-info"]:
            raise GatewayError("tool_error")
    return dict(VERSIONS)


def run_worker(argv: list[str], cwd: Path, env: dict[str, str], *, timeout: float) -> bytes:
    if timeout <= 0:
        raise GatewayError("timeout")
    try:
        with tempfile.TemporaryFile(dir=cwd) as stdout, tempfile.TemporaryFile(dir=cwd) as stderr:
            with subprocess.Popen(
                [sys.executable, "-I", "-c", _LIMIT_EXEC, str(MAX_BYTES), *argv],
                cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                shell=False, start_new_session=True,
            ) as proc:
                try:
                    proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    _kill_group(proc.pid)
                    proc.wait()
                    raise GatewayError("timeout") from None
                except BaseException:
                    _kill_group(proc.pid)
                    proc.wait()
                    raise
                # Reap the leader above; stop any descendant remaining in its group.
                _kill_group(proc.pid)
                if proc.returncode or any(os.fstat(s.fileno()).st_size >= MAX_BYTES for s in (stdout, stderr)):
                    raise GatewayError("tool_error")
                stdout.seek(0)
                return stdout.read(MAX_BYTES)
    except OSError as exc:
        raise GatewayError("tool_error") from exc


def _kill_group(pid: int) -> None:
    try:
        os.killpg(pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


@contextmanager
def scratch_project(db: Path, manifest: bytes, dbt_project: bytes):
    with tempfile.TemporaryDirectory(prefix="cvm-agent-") as directory:
        project = Path(directory)
        for child in ("target", "home", "spill"):
            (project / child).mkdir()
        (project / "target/semantic_manifest.json").write_bytes(manifest)
        (project / "dbt_project.yml").write_bytes(dbt_project)
        credentials = {
            "type": "duckdb",
            "path": str(db),
            "schema": "main",
            "threads": 2,
            "config_options": {
                "access_mode": "READ_ONLY",
                "enable_external_access": False,
                "autoinstall_known_extensions": False,
                "autoload_known_extensions": False,
                "memory_limit": "2GiB",
                "threads": 2,
                "temp_directory": str(project / "spill"),
                "max_temp_directory_size": "32MiB",
            },
        }
        (project / "profiles.yml").write_text(yaml.safe_dump({
            "cvm_demo": {"target": "uat", "outputs": {"uat": credentials}},
        }))
        env = {
            "PATH": os.defpath,
            "HOME": str(project / "home"),
            "TMPDIR": str(project),
            "DBT_PROFILES_DIR": str(project),
            "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
            "DBT_USE_COLORS": "false",
            "METRICFLOW_CLIENT_EMAIL": "anonymous",
            "LC_ALL": "C",
        }
        yield project, env


def metricflow_args(mf: Path, query_args: list[str]) -> list[str]:
    return [str(mf.with_name("python")), "-I", str(ENTRY), str(mf), *query_args]
