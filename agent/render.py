"""Render trusted data in a stable, plain-text terminal format."""
from agent.contracts import QueryResult


def _text(value) -> str:
    # Escape formatting delimiters, markup, terminal controls and newlines.
    return "".join(ch if ch.isprintable() and ch not in "<>|&" else f"\\u{ord(ch):04x}"
                   for ch in str(value))


def render_result(result: QueryResult) -> str:
    intent = result.intent
    provenance = result.provenance
    lines = [
        f"{intent.start_date} through {intent.end_date} (inclusive); grain: {intent.grain}",
        f"Population: {result.population_size} classes in the frozen CVM cohort",
        f"Status: {result.status}",
    ]
    for item in intent.filters:
        lines.append(f"Filter: {item.field} {item.op} " + ", ".join(map(_text, item.values)))
    for metric in intent.metrics:
        lines.append(f"{metric} ({result.units[metric]}): {result.metric_definitions[metric]}")
    if result.rows:
        columns = list(result.rows[0].group)
        lines.append(" | ".join([*columns, "Effective cut", *intent.metrics]))
        for row in result.rows:
            cells = [_text(row.group[column]) for column in columns] + [str(row.effective_cut)]
            for metric in intent.metrics:
                value = row.values[metric]
                coverage = row.coverage[metric]
                amount = "null" if value is None else (
                    format(value, ".2f") if result.units[metric] == "BRL" else format(value, "f")
                )
                cells.append(f"{amount} ({coverage.reported}/{coverage.expected}; {coverage.status})")
            lines.append(" | ".join(cells))
    lines.extend(result.warnings)
    lines.extend([
        f"Release: {_text(provenance.release_id)}; bundle SHA-256: {provenance.bundle_sha256}",
        f"Semantic manifest SHA-256: {provenance.semantic_manifest_sha256}",
        f"Source fingerprint: {provenance.source_fingerprint}",
        f"Gateway code SHA-256: {provenance.gateway_code_sha256}",
        "Sources: " + "; ".join(_text(source) for source in provenance.sources),
        f"Query ID: {result.query_id}; query SHA-256: {result.query_hash}",
    ])
    return "\n".join(lines)
