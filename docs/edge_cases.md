# Edge Cases Handled

> Full list in README: [README.md](../README.md#edge-cases-handled)

## Ingestion
- Empty files, malformed JSON, missing fields → quarantine with reason
- Duplicate run_ids → flagged, first kept
- String coercion for numeric fields
- One bad record does not block valid records

## Dashboard
- Missing DuckDB file → actionable message
- Empty tables → empty states, no crash
- Null metrics → displayed as "—"
- Zero filter matches → info message

## Investigation Agent
- LLM disabled → structured summaries
- Raw SQL / destructive keywords → rejected
- Ambiguous time window → defaults to 7 days, stated explicitly
- Missing metrics → "data not available", no fabrication

## Metadata
- Refresh failure → temp file discarded, last known good preserved
