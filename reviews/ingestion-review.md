# Independent ingestion review

Reviewed 2026-10-28 against `specs/data-contracts.md` and `specs/metrics.md`. Scope: pinned official archives, frozen 60-class cohort and calendar, JSON landing, typed staging and existing PL/flow pipeline. Review did not mutate the main database. Findings refer to the code at review time; implementation was concurrently changing.

## Original findings — resolved on re-review

1. **P2 — New columns bypass the required schema-review gate.** `ingestion/cvm.py:36` allows any header superset, and `transform/models/bronze_classified.sql` accepts the resulting envelope without checking extra keys. The contract requires preservation *and review before typed consumption*. Reproduced with a valid row plus `NEW`: classification is `accepted`. Preserve the bytes/envelope but reject or explicitly gate unknown schema until approved.

2. **P2 — Frozen-calendar divergence can silently lose reported flow.** `bronze_classified.sql` checks date validity and file competence, but neither it nor a downstream test requires membership in `report_calendar`. A cohort observation on an additional valid April date reaches the satellite; the dense-calendar left join in `fct_daily.sql` omits that observation entirely. Gate unexpected cohort dates before publishing, so divergence is explicit. The requested frozen calendar should remain unchanged.

3. **P2 — Reconciliation only checks aggregate capture counts.** `transform/tests/landing_reconciles.sql:1-10` groups all three sides by capture, ignoring archive SHA/member. An omitted row from file A and an extra row from file B cancel. It also never validates the excluded population against total parsed records. The contract calls for reconciliation per archive, with physical counts separate from logical deduplication. Persist parsed row counts and compare raw/classified/rejected/accepted counts at file/member grain.

4. **P2 — Source identifiers claim physical line numbers but use logical record ordinals.** `ingestion/cvm.py:37` enumerates CSV records and `scripts/ingest_cvm.py:27` adds one for the header. CSV permits quoted multiline values. Reproduced a first data record spanning physical lines 2–3: the next record starts on line 4 but gets suffix `3`. This does not lose archive bytes, but breaks the promised SHA/member/physical-line locator. Track `reader.line_num` and record start/end, or explicitly amend the provenance contract to logical CSV record ordinal.

## Other limits to document

- The object store protects against accidental overwrite through this ingestion API and verifies bytes on replay. Mode 0444 is not storage-level WORM protection; an owner can still replace/delete files. No such stronger claim should be made.
- `register()` is atomic for new batch data and now compares replayed envelopes with stored envelopes. Replay still does not compare stored capture metadata, file declarations, or frozen reference tables; parser code/version remains absent from CLI signature and landing capture metadata. Those remain future metadata/corruption-detection limits, not demonstrated errors in the frozen snapshot.
- Investor lexical validation accepts at most ten digits, narrower than the documented nonnegative BIGINT range. Current frozen source may satisfy that bound; document the narrower envelope rule or validate against actual BIGINT limits.

## Positive checks

Archive bytes remain content-addressed; preexisting corruption fails rather than silently repairing. Source monetary/quantity text is retained as strings. Monetary lexical checks precede accepted typed consumption; required invalid values are rejected rather than zero-filled. Net flow widens both operands before subtraction. New registration uses a database transaction and rolls back on exceptions. Identical rows preserve distinct source identifiers through logical deduplication.

## Evidence

An in-memory Python/DuckDB probe imported the production parser, generated a temporary in-memory ZIP, and executed the production bronze SQL with only its dbt source reference replaced by a temporary table. Output: extra-column records `('2', 'accepted'), ('3', 'accepted')`; second record physically on line 4 reported as line 3. No disk database was opened. Calendar and per-file reconciliation findings are direct control-flow/query inspection; no full dbt rebuild was performed by this reviewer.

## Independent re-review after fixes

**No remaining blocking finding for the intended frozen-cohort implementation.** All original P2 findings are addressed: unknown columns are tagged and quarantined, physical start/end lines are tracked and the source ID uses the start, file audit checks each archive rather than capture totals, and an explicit calendar test blocks business descendants.

Executed a fresh temporary copied dbt project and new DuckDB file (`storage_compatibility_version=v1.4.0`), with one synthetic valid source observation registered through the production store. A successful baseline build was followed by three independent adverse builds using the production models/tests:

| Input fault | Quarantine rows | Staging | Satellite / fact | Previously published business tables |
|---|---:|---|---|---|
| unknown_columns envelope | 1 | skipped | skipped | exact row equality with baseline |
| observation outside frozen calendar | 0 | success | skipped | exact row equality with baseline |
| declared file count mismatch | 0 | skipped | skipped | exact row equality with baseline |

All adverse builds failed as intended. Preservation comparison covered `sat_daily_report`, `current_daily`, and `fct_daily`. This independently verifies that quarantine materializes before business staging is skipped, and that rejected publication retains the previous business result. The temporary project/database were removed on completion; no main database or implementation files were changed.

Also independently ran `python -m unittest discover -s tests/ingestion -v`: **13 tests passed**, including physical multiline provenance, unknown-column quarantine annotation, replay idempotence, missing-envelope replay detection, changed signature rejection, and full batch rollback on duplicate source identity.

Residual audit limitation: `source_records` is calculated as `declared_enveloped + excluded`, rather than checked against an independently persisted archive record total. Per-file envelope/accepted/rejected reconciliation now prevents offsetting loss between files; excluded-row enumeration still relies on the parser traversal. This does not block the frozen-source delivery with its external oracle checks, but should not be described as independent verification of all excluded rows.

## Final timestamp compatibility check

Independently inspected the final `captures.sql` expression `make_timestamp(epoch_us(captured_at))` and executed it in an in-memory DuckDB connection. Inputs `2026-10-28T12:34:56.123456+00:00` and `2026-10-28T09:34:56.123456-03:00` both yielded the identical UTC-naive timestamp `2026-10-28 12:34:56.123456`. Repeated under session timezones UTC, America/Sao_Paulo, and Asia/Tokyo; every result matched and preserved microseconds. No issue found with the replacement expression. This reviewer did not independently rerun the strict dbt analyzer after this last compatibility adjustment.
