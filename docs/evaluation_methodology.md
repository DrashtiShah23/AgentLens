# Evaluation Methodology

All evaluators are **deterministic**. No LLM is called.

## Scorers

| Evaluator | Method |
|---|---|
| Correctness | Numeric tolerance or keyword overlap |
| SQL | sqlglot parse, allowed tables/columns, no destructive SQL |
| Tool | Required tool, status, input/output checks |
| Retrieval | Relevance threshold, chunk usage |
| Format | Non-empty answer, JSON for classification tasks |
| Latency | Threshold tiers (good / degraded / fail) |
| Cost | USD threshold tiers |

## Overall Score

Task-aware weighted average. Null component scores are **excluded** and weights redistributed — never treated as zero.
