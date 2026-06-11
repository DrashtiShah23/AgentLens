# Failure Taxonomy

| Category | Primary Signals |
|---|---|
| hallucination | Low correctness, retrieval exists |
| retrieval_failure | Low retrieval score |
| tool_failure | Failed/skipped tool, low tool score |
| sql_failure | SQL parse/semantic error |
| prompt_regression | Low score on prompt_v5 |
| reasoning_failure | Good components, wrong answer |
| format_failure | Low format score |
| latency_failure | Latency score zero |
| cost_failure | Cost score zero |
| pipeline_failure | Duplicate run_id, ingestion error |
| unknown | Ambiguous signals |

## Severity

- **critical** — very low overall score
- **high** — hallucination/SQL failures, high failure rates
- **medium** — latency/cost spikes, tool issues
- **low** — low confidence, minor issues
