# LLM Cost Design

## Hard Rule

**LLM is never called per agent run.**

At 1M runs, even $0.0002/run = $200+. Per-run LLM evaluation is also less accurate than deterministic checks for structured signals.

## When LLM Is Used

Only when:
1. A human asks an investigation question
2. `OBSERVATORY_USE_LLM=true`

Default: `OBSERVATORY_USE_LLM=false` — agent returns structured metric summaries.

## Cost Model

- Investigation query: ~$0.0001–$0.0003 (gpt-4o-mini / claude-haiku)
- $15 budget ≈ 50,000–75,000 investigation queries
- Base platform cost: **$0.00**
