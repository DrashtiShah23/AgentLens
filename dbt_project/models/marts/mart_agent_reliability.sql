select
    r.agent_name,
    cast(r.started_at as date) as run_date,
    count(*) as total_runs,
    avg(e.overall_score) as reliability_score,
    {{ safe_divide('sum(case when e.overall_score < 0.7 then 1 else 0 end)', 'count(*)') }} as failure_rate,
    avg(r.latency_ms) as avg_latency_ms,
    avg(r.estimated_cost_usd) as avg_cost_usd
from {{ ref('stg_agent_runs') }} r
join {{ ref('stg_evaluation_results') }} e on r.run_id = e.run_id
where r.is_duplicate = false
group by r.agent_name, cast(r.started_at as date)
