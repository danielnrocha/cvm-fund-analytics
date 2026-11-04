"""A pinned, single-session adapter for validated MetricFlow queries."""
import hashlib
import json
import re
import time
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from uuid import uuid4

from pydantic import ValidationError

from agent.catalog import (
    DIMENSIONS, METRICS, POLICY, SEMANTIC_MANIFEST, Catalog, canonical, sha256,
)
from agent.contracts import GatewayError, Provenance, QueryIntent, QueryResult
from agent.results import checked_rows, parse_csv
from agent.worker import (
    MAX_BYTES, inspect_runtime, metricflow_args, run_worker, scratch_project,
)
from release.snapshots import _verify, resolve

DB = "snapshot.duckdb"
PROJECT = "project/dbt_project.yml"
VALIDATION = "validation.json"
SOURCES = ("specs/metrics.md", "Frozen CVM daily fund reports")
_MAX_EXPLAINS = 16
_GATEWAY_FILES = ("_mf_entry.py", "catalog.py", "contracts.py", "gateway.py", "render.py",
                  "results.py", "worker.py")


class Gateway:
    def __init__(self, release_root: Path, mf_executable: Path, *, release_id: str | None = None):
        self._mf = Path(mf_executable)
        self._versions = inspect_runtime(self._mf)
        self._lock = Lock()
        code_dir = Path(__file__).resolve().parent
        code = {path: (code_dir / path).read_bytes() for path in _GATEWAY_FILES}
        self._worker_entry = code["_mf_entry.py"]
        self._code_hash = sha256(canonical({path: sha256(data) for path, data in code.items()}))
        self._explanations: OrderedDict[str, str] = OrderedDict()
        try:
            root = Path(release_root).resolve()
            bundle = (resolve(root, "uat") if release_id is None else _verify(root, release_id)).resolve()
            metadata = (bundle / "bundle.json").read_bytes()
            hashes = json.loads(metadata)["files"]
            self._release_id = bundle.name
            self._bundle_hash = sha256(metadata)
            self._db = bundle / DB
            self._db_hash = hashes[DB]
            self._manifest = _bound_file(bundle, hashes, SEMANTIC_MANIFEST)
            self._dbt_project = _bound_file(bundle, hashes, PROJECT)
            validation = json.loads(_bound_file(bundle, hashes, VALIDATION))
            fingerprints = validation["source_hashes"]
            self._catalog = Catalog(self._manifest, fingerprints)
            self._source_fingerprint = sha256(canonical(fingerprints))
            revision = validation.get("source_revision")
            self._source_revision = revision if isinstance(revision, str) and re.fullmatch(
                r"[0-9a-f]{40}", revision
            ) else None
            self._manifest_hash = hashes[SEMANTIC_MANIFEST]
            self._check_db()
        except (OSError, KeyError, TypeError, ValueError) as exc:
            raise GatewayError("snapshot_invalid") from exc

    def _check_db(self, deadline: float | None = None) -> None:
        try:
            if self._db.is_symlink() or self._db.with_suffix(".duckdb.wal").exists():
                raise GatewayError("snapshot_invalid")
            digest = hashlib.sha256()
            with self._db.open("rb") as stream:
                while True:
                    if deadline is not None:
                        _check_deadline(deadline)
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
            if deadline is not None:
                _check_deadline(deadline)
            if digest.hexdigest() != self._db_hash:
                raise GatewayError("snapshot_invalid")
        except OSError as exc:
            raise GatewayError("snapshot_invalid") from exc

    def get_catalog(self) -> dict:
        return {
            **self._catalog.get_catalog(),
            "release_id": self._release_id,
            "semantic_manifest_sha256": self._manifest_hash,
        }

    def describe_metric(self, metric_id: str) -> dict:
        return self._catalog.describe_metric(metric_id)

    def explain_query(self, query_id: str) -> str:
        try:
            return self._explanations[query_id]
        except KeyError:
            raise GatewayError("unsupported_capability") from None

    def query_metrics(self, intent: QueryIntent, *, deadline: float | None = None) -> QueryResult:
        """Run one validated intent within the caller's optional monotonic deadline."""
        if not self._lock.acquire(blocking=False):
            raise GatewayError("tool_error")
        try:
            return self._query(intent, deadline=deadline)
        finally:
            self._lock.release()

    def _query(self, intent: QueryIntent, *, deadline: float | None) -> QueryResult:
        start = time.monotonic()
        deadline = start + 60 if deadline is None else min(start + 60, deadline)
        _check_deadline(deadline)
        # Frozen models still contain mutable lists. Revalidate a detached copy
        # at the execution boundary, including model_construct() callers.
        try:
            if type(intent) is not QueryIntent:
                raise GatewayError("invalid_plan")
            intent = QueryIntent.model_validate(intent.model_dump(warnings=False))
        except (ValidationError, ValueError, TypeError) as exc:
            raise GatewayError("invalid_plan") from exc

        members, buckets, where = self._catalog.bind(intent)
        metrics = tuple(dict.fromkeys(
            intent.metrics + [count for metric in intent.metrics for count in METRICS[metric][3]]
        ))
        group_keys = tuple(
            ([f"metric_time__{intent.grain}"] if intent.grain != "total" else [])
            + [DIMENSIONS[dimension] for dimension in intent.dimensions]
        )
        args = ["query", "--metrics", ",".join(metrics), "--start-time", intent.start_date,
                "--end-time", intent.end_date, "--limit", "501", "--quiet"]
        if group_keys:
            args.extend(("--group-by", ",".join(group_keys), "--order", ",".join(group_keys)))
        if intent.grain == "month":
            # MetricFlow expands CLI time flags to cover the enclosing months.
            # Both date strings passed strict ISO/calendar validation above.
            exact_days = ("{{ TimeDimension('metric_time', 'day') }} "
                          f"BETWEEN '{intent.start_date}' AND '{intent.end_date}'")
            where = f"{exact_days} AND {where}" if where else exact_days
        if where:
            args.extend(("--where", where))
        query_hash = sha256(canonical({
            "policy": POLICY, "bundle": self._bundle_hash, "manifest": self._manifest_hash,
            "engines": self._versions, "gateway_code": self._code_hash,
            "intent": intent.model_dump(mode="json"), "arguments": args,
        }))
        query_id = uuid4().hex
        raw = sql = None
        rows = ()
        self._check_db(deadline)
        if not buckets:
            status = "no_expected_observations"
        elif not members:
            status = "empty"
        else:
            raw, sql = self._query_pair(args, deadline)
            self._check_db(deadline)
            if raw is None:
                # CLI 0.15.0 emits no CSV on empty output. A nonempty known
                # population/calendar must still have rows under this contract.
                raise GatewayError("result_invalid")
            rows = checked_rows(parse_csv(raw, group_keys, metrics), intent, members, buckets, metrics)
            status = "partial" if any(
                cell.status == "partial" for row in rows for cell in row.coverage.values()
            ) else "ok"
        warnings = {
            "partial": ("Some expected reports are missing; amounts are reported values.",),
            "no_expected_observations": ("The requested interval has no expected reporting dates.",),
            "empty": ("No reporting classes match the combined filters.",),
            "ok": (),
        }[status]
        result = QueryResult(
            query_id=query_id, query_hash=query_hash, intent=intent, population_size=len(members),
            metric_definitions={m: METRICS[m][1] for m in intent.metrics},
            units={m: METRICS[m][0] for m in intent.metrics},
            provenance=Provenance(
                release_id=self._release_id, bundle_sha256=self._bundle_hash,
                semantic_manifest_sha256=self._manifest_hash, source_revision=self._source_revision,
                source_fingerprint=self._source_fingerprint, gateway_code_sha256=self._code_hash,
                engine_versions=dict(self._versions),
                raw_result_sha256=sha256(raw) if raw is not None else None,
                compiled_sql_sha256=sha256(sql) if sql is not None else None, sources=SOURCES,
            ),
            rows=rows, status=status, warnings=warnings, elapsed_ms=int((time.monotonic()-start)*1000),
        )

        _check_deadline(deadline)
        if sql:
            self._explanations[query_id] = sql.decode("utf-8").strip()
            if len(self._explanations) > _MAX_EXPLAINS:
                self._explanations.popitem(last=False)
        return result

    def _query_pair(self, args: list[str], deadline: float) -> tuple[bytes | None, bytes]:
        try:
            with scratch_project(self._db, self._manifest, self._dbt_project) as (project, env):
                output = project / "result.csv"
                entry = project / "_mf_entry.py"
                entry.write_bytes(self._worker_entry)
                command = metricflow_args(self._mf, entry, args)
                sql = run_worker(
                    command + ["--explain", "--csv", str(output)], project, env,
                    timeout=min(30, _check_deadline(deadline)),
                ).strip()
                sql.decode("utf-8")
                if not sql.startswith((b"SELECT", b"WITH")) or output.exists():
                    raise GatewayError("tool_error")
                self._check_db(deadline)
                if (project / "target/semantic_manifest.json").read_bytes() != self._manifest:
                    raise GatewayError("snapshot_invalid")
                executed_sql = run_worker(
                    command + ["--csv", str(output)], project, env,
                    timeout=min(30, _check_deadline(deadline)),
                ).strip()
                if executed_sql != sql:
                    raise GatewayError("result_invalid")
                if (project / "target/semantic_manifest.json").read_bytes() != self._manifest:
                    raise GatewayError("snapshot_invalid")
                if not output.exists():
                    return None, sql
                if output.stat().st_size >= MAX_BYTES:
                    raise GatewayError("tool_error")
                _check_deadline(deadline)
                raw = output.read_bytes()
                _check_deadline(deadline)
                return raw, sql
        except (OSError, UnicodeError) as exc:
            raise GatewayError("tool_error") from exc


def _check_deadline(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise GatewayError("timeout")
    return remaining


def _bound_file(bundle: Path, hashes: dict[str, str], relative: str) -> bytes:
    data = (bundle / relative).read_bytes()
    if sha256(data) != hashes[relative]:
        raise GatewayError("snapshot_invalid")
    return data
