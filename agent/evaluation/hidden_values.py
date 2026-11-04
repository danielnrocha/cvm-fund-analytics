"""Synthetic numeric qualification cases isolated from planner context."""
import json
import shutil
import subprocess
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.contracts import QueryIntent, QueryResult
from agent.worker import inspect_runtime
from release.snapshots import _verify, seal

RELEASE_ID = "cvm-qualification-hidden-values-v1"
CLASSES = ("CVM:CLASS:621", "CVM:CLASS:1024")
METRICS = ("reported_net_assets_eop", "net_flow")
# Keys and assigned facts are explicit. The tests use separately calculated totals.
FACTS = (
    (CLASSES[0], "2026-04-01", "123456.78", "1234.57", 1),
    (CLASSES[1], "2026-04-01", "234567.89", "-741.11", 1),
    (CLASSES[0], "2026-04-02", "987654.23", "0.00", 1),
    (CLASSES[1], "2026-04-02", None, None, 0),
)
_MUTATE = """
import json, sys
from datetime import date
from decimal import Decimal
import duckdb

read = '''SELECT entity_id, report_date, observation_id, classification_at_capture,
                 expected, pl, net_flow, reported FROM main.fct_daily'''

def facts(conn):
    rows = conn.execute(read).fetchall()
    by_key = {(entity, day): tuple(values) for entity, day, *values in rows}
    assert len(rows) == len(by_key) == 7560
    assert len({entity for entity, day in by_key}) == 60
    return by_key

path = sys.argv[1]
with duckdb.connect(path, config={'enable_external_access': 'false',
                                  'autoinstall_known_extensions': 'false',
                                  'autoload_known_extensions': 'false'}) as conn:
    expected = facts(conn)
    for entity, iso_day, pl, flow, reported in json.loads(sys.argv[2]):
        key = entity, date.fromisoformat(iso_day)
        before = expected[key]
        assert before[2] == 1
        values = tuple(None if amount is None else Decimal(amount) for amount in (pl, flow))
        assert before[3:] != (*values, reported)
        expected[key] = (*before[:3], *values, reported)
        conn.execute('''UPDATE main.fct_daily SET pl = ?, net_flow = ?, reported = ?
                        WHERE entity_id = ? AND report_date = ?''', [*values, reported, *key])
with duckdb.connect(path, read_only=True) as conn:
    assert facts(conn) == expected
"""


def seal_hidden_values(baseline: Path, release_root: Path, mf_executable: Path) -> Path:
    """Verify the sealed input, independently check the four fact changes, and seal."""
    baseline = Path(baseline).absolute()
    if baseline.parent.name != "snapshots":
        raise ValueError("Baseline must be a sealed snapshot directory")
    baseline_root = baseline.parents[1].resolve()
    release_root = Path(release_root).resolve()
    if release_root.is_relative_to(baseline_root):
        raise ValueError("Qualification release root must be separate from the baseline")
    baseline = _verify(baseline_root, baseline.name)
    mf_executable = Path(mf_executable)
    inspect_runtime(mf_executable)
    source = json.loads((baseline / "bundle.json").read_text())
    validation = json.loads((baseline / "validation.json").read_text())
    with TemporaryDirectory(prefix="cvm-hidden-values-") as scratch:
        candidate = Path(scratch)
        for relative in ("snapshot.duckdb", "project/dbt_project.yml",
                         "project/target/semantic_manifest.json"):
            dest = candidate / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(baseline / relative, dest)
        subprocess.run(
            [str(mf_executable.with_name("python")), "-I", "-c", _MUTATE,
             str(candidate / "snapshot.duckdb"), json.dumps(FACTS)],
            check=True, timeout=30, capture_output=True, cwd=candidate,
            env={"HOME": str(candidate), "TMPDIR": str(candidate)},
        )
        (candidate / "validation.json").write_text(json.dumps({
            "passed": True,
            "synthetic_qualification_only": True,
            "base_release_id": baseline.name,
            "base_database_sha256": source["files"]["snapshot.duckdb"],
            "checked_fact_changes": len(FACTS),
            "source_hashes": validation["source_hashes"],
        }, sort_keys=True))
        _verify(baseline.parents[1], baseline.name)
        return seal(release_root, candidate, RELEASE_ID)


@dataclass(frozen=True)
class HiddenValueCase:
    question: str
    intent: QueryIntent
    # Group key, closing PL, interval flow, reported/expected closing and period pairs.
    expected: tuple[tuple[str | None, str | None, str | None, tuple[int, int], tuple[int, int]], ...]

    def check(self, result: QueryResult) -> None:
        assert result.status == "partial" and result.population_size == len(CLASSES)
        for row, (entity, pl, flow, closing, period) in zip(result.rows, self.expected, strict=True):
            assert row.group == ({} if entity is None else {"reporting_entity": entity})
            assert row.effective_cut.isoformat() == "2026-04-02"
            for metric, value, counts in zip(METRICS, (pl, flow), (closing, period), strict=True):
                assert row.values[metric] == (None if value is None else Decimal(value))
                coverage = row.coverage[metric]
                assert (coverage.reported, coverage.expected) == counts
                assert coverage.status == ("complete" if counts[0] == counts[1] else "partial")


def hidden_value_cases() -> tuple[HiddenValueCase, ...]:
    def intent(start: str, dimensions: list[str]) -> QueryIntent:
        return QueryIntent.model_validate({
            "action": "query", "metrics": list(METRICS), "start_date": start, "end_date": "2026-04-02",
            "grain": "total", "dimensions": dimensions, "presentation": "table",
            "filters": [{"field": "reporting_entity", "op": "in", "values": list(CLASSES)}],
        })

    return (
        HiddenValueCase(
            "Show combined closing reported net assets and reported net flow from April 1 through "
            "April 2, 2026 for CVM:CLASS:621 and CVM:CLASS:1024 only.",
            intent("2026-04-01", []),
            ((None, "987654.23", "493.46", (1, 2), (3, 4)),),
        ),
        HiddenValueCase(
            "Show closing reported net assets and reported net flow for April 2, 2026, separately "
            "for CVM:CLASS:621 and CVM:CLASS:1024 only.",
            intent("2026-04-02", ["reporting_entity"]),
            ((CLASSES[1], None, None, (0, 1), (0, 1)),
             (CLASSES[0], "987654.23", "0.00", (1, 1), (1, 1))),
        ),
    )
