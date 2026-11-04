"""Untrusted planner input and typed gateway output."""
from datetime import date
from decimal import Decimal
from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


Metric = Literal["reported_net_assets_eop", "net_flow", "reporting_coverage_eop",
                 "reporting_coverage_period"]
Dimension = Literal["reporting_entity", "classification_at_capture"]
Grain = Literal["total", "month", "day"]
IsoDate = Annotated[str, StringConstraints(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")]
FilterValue = Annotated[str, StringConstraints(min_length=1, max_length=80)]
FailureCode = Literal["invalid_plan", "unsupported_capability", "outside_snapshot",
                      "too_many_rows", "snapshot_invalid", "timeout", "tool_error", "result_invalid"]


class GatewayError(Exception):
    def __init__(self, code: FailureCode):
        self.code = code
        super().__init__(code)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class Filter(StrictModel):
    field: Dimension
    op: Literal["eq", "in"]
    values: list[FilterValue] = Field(min_length=1, max_length=20)

    @model_validator(mode="after")
    def validate_values(self) -> Self:
        if self.op == "eq" and len(self.values) != 1:
            raise ValueError("eq requires exactly one value")
        if len(set(self.values)) != len(self.values):
            raise ValueError("filter values must be unique")
        return self


class QueryIntent(StrictModel):
    action: Literal["query"]
    metrics: list[Metric] = Field(min_length=1, max_length=3)
    start_date: IsoDate
    end_date: IsoDate
    grain: Grain
    dimensions: list[Dimension] = Field(max_length=2)
    filters: list[Filter] = Field(max_length=4)
    presentation: Literal["table", "chart"]

    @field_validator("start_date", "end_date")
    @classmethod
    def calendar_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value

    @model_validator(mode="after")
    def validate_query(self) -> Self:
        if self.start_date > self.end_date:
            raise ValueError("end_date must be on or after start_date")
        if len(set(self.metrics)) != len(self.metrics):
            raise ValueError("metrics must be unique")
        if len(set(self.dimensions)) != len(self.dimensions):
            raise ValueError("dimensions must be unique")
        return self


class ClarifyIntent(StrictModel):
    action: Literal["clarify"]
    reason: Literal["missing_period", "ambiguous_metric", "unknown_entity", "ambiguous_entity",
                    "ambiguous_population", "ambiguous_request"]
    missing_slots: list[Literal["metric", "period", "entity", "population", "grain"]] = Field(
        min_length=1, max_length=5
    )


class UnsupportedIntent(StrictModel):
    action: Literal["unsupported"]
    reason: Literal["outside_snapshot", "unsupported_metric", "unsupported_dimension",
                    "unsupported_capability", "causality", "financial_advice"]
    alternatives: list[Metric] = Field(default_factory=list, max_length=3)


Decision = Annotated[QueryIntent | ClarifyIntent | UnsupportedIntent, Field(discriminator="action")]


class Coverage(StrictModel):
    reported: int
    expected: int
    status: Literal["complete", "partial", "undefined"]


class ResultRow(StrictModel):
    group: dict[str, str]
    effective_cut: date
    values: dict[str, Decimal | None]
    coverage: dict[str, Coverage]
    supporting_counts: dict[str, int]


class Provenance(StrictModel):
    release_id: str
    bundle_sha256: str
    semantic_manifest_sha256: str
    source_revision: str | None
    source_fingerprint: str
    gateway_code_sha256: str
    engine_versions: dict[str, str]
    raw_result_sha256: str | None
    compiled_sql_sha256: str | None
    sources: tuple[str, ...]


class QueryResult(StrictModel):
    query_id: str
    query_hash: str
    intent: QueryIntent
    population_size: int
    metric_definitions: dict[str, str]
    units: dict[str, str]
    provenance: Provenance
    rows: tuple[ResultRow, ...]
    status: Literal["ok", "partial", "empty", "no_expected_observations"]
    warnings: tuple[str, ...]
    elapsed_ms: int
