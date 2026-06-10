select
    r.model_name,
    r.task_type,
    count(*) as run_count,
    avg(e.overall_score) as avg_reliability_score,
    avg(e.correctness_score) as avg_correctness_score,
    avg(e.sql_score) as avg_sql_score,
    avg(e.retrieval_score) as avg_retrieval_score,
    avg(e.tool_score) as avg_tool_score,
    avg(r.latency_ms) as avg_latency_ms,
    avg(r.estimated_cost_usd) as avg_cost_usd,
    {{ safe_divide('sum(case when e.overall_score < 0.7 then 1 else 0 end)', 'count(*)') }} as failure_rate
from {{ ref('stg_agent_runs') }} r
left join {{ ref('stg_evaluation_results') }} e on r.run_id = e.run_id
where r.is_duplicate = false
group by r.model_name, r.task_type
