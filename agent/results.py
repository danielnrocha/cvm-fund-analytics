"""Bounded CSV decoding and result checks independent of presentation."""
import csv
import io
import re
from decimal import Decimal, InvalidOperation, localcontext

from agent.catalog import COUNTS, CLOSING, METRICS
from agent.contracts import Coverage, GatewayError, ResultRow

MAX_ROWS = 500


def parse_csv(raw: bytes, group_keys: tuple[str, ...], metrics: tuple[str, ...]) -> dict:
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8")), strict=True)
        header = reader.fieldnames or []
        if len(header) != len(set(header)) or set(header) != set(group_keys + metrics):
            raise ValueError("Unexpected result columns")
        rows = {}
        for row in reader:
            if len(rows) == MAX_ROWS:
                raise GatewayError("too_many_rows")
            if None in row or any(value is None for value in row.values()):
                raise ValueError("Malformed row")
            key = tuple(_group_value(column, row[column]) for column in group_keys)
            if key in rows:
                raise ValueError("Duplicate group")
            rows[key] = {metric: _number(metric, row[metric]) for metric in metrics}
        return rows
    except (ValueError, InvalidOperation, csv.Error) as exc:
        raise GatewayError("result_invalid") from exc


def _group_value(column: str, value: str) -> str:
    if column.startswith("metric_time__"):
        match = re.fullmatch(r"([0-9]{4}-[0-9]{2}-[0-9]{2})(?:[ T]00:00:00)?", value)
        if match:
            return match.group(1)
    elif value:
        return value
    raise ValueError("Invalid group")


def _number(metric: str, value: str):
    if not value:
        return None
    if metric in COUNTS:
        if not re.fullmatch(r"[0-9]{1,8}", value):
            raise ValueError("Non-integral count")
        return int(value)
    if metric in METRICS and METRICS[metric][0] == "BRL":
        if not re.fullmatch(r"-?[0-9]{1,36}(?:\.[0-9]{1,2})?", value):
            raise ValueError("Invalid money or lost decimal format")
    elif not re.fullmatch(r"(?:[0-9]+(?:\.[0-9]+)?)(?:[eE][+-]?[0-9]{1,3})?", value) or len(value) > 64:
        raise ValueError("Invalid ratio")
    return Decimal(value)


def checked_rows(parsed, intent, members, buckets, actual_metrics):
    """Compare groups and denominators to independently pinned calendar/cohort."""
    expected = {}
    for label, dates in buckets.items():
        prefix = (label,) if intent.grain != "total" else ()
        if intent.dimensions:
            expected.update({prefix + (member,): (dates, 1) for member in members})
        elif members:
            expected[prefix] = dates, len(members)
    if set(parsed) != set(expected):
        raise GatewayError("result_invalid")
    rows = []
    for key, row in sorted(parsed.items()):
        dates, member_count = expected[key]
        values, coverage = {}, {}
        for metric in intent.metrics:
            unit, _, _, pair, *_ = METRICS[metric]
            reported, denominator = (row[name] for name in pair)
            expected_count = member_count * (1 if pair == CLOSING else len(dates))
            if (not isinstance(reported, int) or denominator != expected_count
                    or not 0 <= reported <= denominator):
                raise GatewayError("result_invalid")
            coverage[metric] = Coverage(
                reported=reported, expected=denominator,
                status="complete" if reported == denominator else "partial",
            )
            value = row[metric]
            if unit == "BRL" and (value is None) != (reported == 0):
                raise GatewayError("result_invalid")
            if unit == "ratio":
                with localcontext() as context:
                    context.prec = 28
                    ratio = Decimal(reported) / Decimal(denominator)
                    if value is None or abs(value - ratio) > Decimal("0.000000000001"):
                        raise GatewayError("result_invalid")
                    value = ratio
            values[metric] = value
        group_labels = ([f"metric_time__{intent.grain}"] if intent.grain != "total" else []) + intent.dimensions
        rows.append(ResultRow(
            group=dict(zip(group_labels, key, strict=True)), effective_cut=dates[-1],
            values=values, coverage=coverage,
            supporting_counts={m: row[m] for m in actual_metrics if m in COUNTS},
        ))
    return tuple(rows)
