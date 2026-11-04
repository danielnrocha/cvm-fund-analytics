"""Reviewed contract layered over the pinned semantic manifest and frozen inputs."""
import csv
import hashlib
import io
import json
import re
from datetime import date
from pathlib import Path

from agent.contracts import GatewayError, QueryIntent

ROOT = Path(__file__).resolve().parents[1]
COHORT = "profiling/cvm/evidence/cohort.csv"
CALENDAR = "profiling/cvm/evidence/calendar.json"
SEMANTIC_MANIFEST = "project/target/semantic_manifest.json"
FIRST = date(2026, 4, 1)
LAST = date(2026, 9, 30)
POLICY = "cvm-agent-v1"
# Baseline and reviewed refactor share this structural definition. Descriptions
# are documentary only; the full published manifest has its own bound hash.
REVIEWED_DEFINITION = "4c762e156ab6a5bd6383a3a4600e01a4005afdef489dcc25aa3ce18c070caad9"

CLOSING = ("reporting_entities_eop", "expected_entities_eop")
PERIOD = ("reporting_observations", "expected_observations")
COUNTS = frozenset(CLOSING + PERIOD)
DIMENSIONS = {
    "reporting_entity": "reporting_entity",
    "classification_at_capture": "observation__classification_at_capture",
}
GROUPINGS = ((), ("reporting_entity",))
METRICS = {
    "reported_net_assets_eop": (
        "BRL", "Sum of reported net assets at the common closing date.", "common closing date",
        CLOSING, ("PL", "reported net assets"), "Do not sum daily or monthly closings.",
    ),
    "net_flow": (
        "BRL", "Sum of reported subscriptions minus redemptions.", "sum over the interval",
        PERIOD, ("net flow", "net subscriptions"), "Gross subscriptions are not net flow.",
    ),
    "reporting_coverage_eop": (
        "ratio", "Reporting classes divided by expected classes at the common closing date.",
        "ratio of closing counts", CLOSING, ("closing coverage",), "Coverage is not certification.",
    ),
    "reporting_coverage_period": (
        "ratio", "Observed reports divided by expected class/day reports.",
        "ratio of interval counts", PERIOD, ("interval coverage",), "Do not average subgroup ratios.",
    ),
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical(data) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _definition(value):
    if isinstance(value, dict):
        return {k: _definition(v) for k, v in value.items() if k != "description"}
    if isinstance(value, list):
        return [_definition(v) for v in value]
    return value


class Catalog:
    def __init__(self, manifest: bytes, fingerprints: dict[str, str]):
        if sha256(canonical(_definition(json.loads(manifest)))) != REVIEWED_DEFINITION:
            raise ValueError("Unreviewed semantic definition")
        cohort, calendar = ((ROOT / path).read_bytes() for path in (COHORT, CALENDAR))
        for path, value in ((COHORT, cohort), (CALENDAR, calendar)):
            if sha256(value) != fingerprints[path]:
                raise ValueError("Frozen input fingerprint mismatch")
        self.classes = {
            "CVM:CLASS:" + row["ID_Registro_Classe"]: row["Classificacao"]
            for row in csv.DictReader(io.StringIO(cohort.decode()))
        }
        self.dates = tuple(date.fromisoformat(row["date"]) for row in json.loads(calendar))
        if (len(self.classes) != 60 or len(self.dates) != 126
                or list(self.dates) != sorted(set(self.dates))
                or (self.dates[0], self.dates[-1]) != (FIRST, LAST)):
            raise ValueError("Unexpected frozen population or calendar")

    def describe_metric(self, metric_id: str) -> dict:
        if metric_id not in METRICS:
            raise GatewayError("unsupported_capability")
        unit, definition, aggregation, counts, synonyms, counterexample = METRICS[metric_id]
        return {
            "id": metric_id,
            "unit": unit,
            "definition": definition,
            "source": "Frozen CVM daily fund reports",
            "population": "60 reporting classes in the frozen cohort, before filters",
            "grains": ["total", "month", "day"],
            "time_aggregation": aggregation,
            "missing_policy": "Absent amounts remain null; zero denominator leaves ratio undefined.",
            "coverage_counts": list(counts),
            "supported_groupings": [list(grouping) for grouping in GROUPINGS],
            "synonyms": list(synonyms),
            "counterexample": counterexample,
        }

    def get_catalog(self) -> dict:
        return {
            "policy": POLICY,
            "start_date": FIRST.isoformat(),
            "end_date": LAST.isoformat(),
            "metrics": [self.describe_metric(metric) for metric in METRICS],
            "filter_values": {
                "reporting_entity": sorted(self.classes),
                "classification_at_capture": sorted(set(self.classes.values())),
            },
            "presentation": ["table"],
        }

    def bind(self, intent: QueryIntent):
        start, end = date.fromisoformat(intent.start_date), date.fromisoformat(intent.end_date)
        if start < FIRST or end > LAST:
            raise GatewayError("outside_snapshot")
        if intent.presentation != "table" or tuple(intent.dimensions) not in GROUPINGS:
            raise GatewayError("unsupported_capability")
        members = set(self.classes)
        where = []
        for item in intent.filters:
            domain = self.classes if item.field == "reporting_entity" else set(self.classes.values())
            if not set(item.values) <= set(domain):
                raise GatewayError("invalid_plan")
            if item.field == "reporting_entity":
                members.intersection_update(item.values)
                column = "{{ Entity('reporting_entity') }}"
            else:
                members.intersection_update(e for e, c in self.classes.items() if c in item.values)
                column = "{{ Dimension('observation__classification_at_capture') }}"
            values = [_sql_literal(value) for value in item.values]
            where.append(f"{column} = {values[0]}" if item.op == "eq"
                         else f"{column} IN ({', '.join(values)})")
        buckets: dict[str, list[date]] = {}
        for day in self.dates:
            if start <= day <= end:
                label = {"total": "", "month": day.replace(day=1).isoformat(),
                         "day": day.isoformat()}[intent.grain]
                buckets.setdefault(label, []).append(day)
        if len(buckets) * (len(members) if intent.dimensions else bool(members)) > 500:
            raise GatewayError("too_many_rows")
        return tuple(sorted(members)), buckets, " AND ".join(where)


def _sql_literal(value: str) -> str:
    # Membership is checked first. This additionally rejects Jinja syntax,
    # controls and escape characters even in a future approved cohort.
    if not re.fullmatch(r"[\w .&'/-]+", value.replace("CVM:CLASS:", ""), re.UNICODE):
        raise GatewayError("invalid_plan")
    return "'" + value.replace("'", "''") + "'"
