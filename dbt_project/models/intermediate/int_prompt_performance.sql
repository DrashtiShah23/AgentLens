select
    r.prompt_version_id,
    r.agent_name,
    count(*) as run_count,
    {{ safe_divide('sum(case when e.overall_score < 0.7 then 1 else 0 end)', 'count(*)') }} as failure_rate,
    avg(e.overall_score) as avg_reliability_score,
    avg(r.latency_ms) as avg_latency_ms,
    avg(r.estimated_cost_usd) as avg_cost_usd,
    sum(case when f.primary_category is not null then 1 else 0 end) as failure_count
from {{ ref('stg_agent_runs') }} r
left join {{ ref('stg_evaluation_results') }} e on r.run_id = e.run_id
left join failure_modes f on r.run_id = f.run_id
where r.is_duplicate = false
group by r.prompt_version_id, r.agent_name
