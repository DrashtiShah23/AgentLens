select
    model_name,
    task_type,
    run_count,
    avg_reliability_score as reliability_score,
    avg_correctness_score as correctness_score,
    avg_sql_score as sql_score,
    avg_retrieval_score as retrieval_score,
    avg_tool_score as tool_score,
    avg_latency_ms,
    avg_cost_usd,
    failure_rate
from {{ ref('int_model_performance') }}
