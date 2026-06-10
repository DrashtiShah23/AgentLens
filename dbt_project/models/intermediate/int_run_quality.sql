select
    r.run_id,
    r.agent_name,
    r.task_type,
    r.prompt_version_id,
    r.model_name,
    r.started_at,
    r.latency_ms,
    r.estimated_cost_usd,
    r.success_flag,
    r.is_duplicate,
    e.overall_score,
    e.correctness_score,
    e.sql_score,
    e.tool_score,
    e.retrieval_score,
    e.format_score,
    e.latency_score,
    e.cost_score,
    case
        when e.overall_score >= 0.85 then 'excellent'
        when e.overall_score >= 0.70 then 'good'
        when e.overall_score >= 0.50 then 'degraded'
        else 'poor'
    end as quality_label
from {{ ref('stg_agent_runs') }} r
left join {{ ref('stg_evaluation_results') }} e on r.run_id = e.run_id
where r.is_duplicate = false
