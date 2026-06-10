select
    cast(r.started_at as date) as run_date,
    r.agent_name,
    r.model_name,
    count(*) as run_count,
    avg(r.latency_ms) as avg_latency_ms,
    max(r.latency_ms) as max_latency_ms,
    avg(r.estimated_cost_usd) as avg_cost_usd,
    max(r.estimated_cost_usd) as max_cost_usd,
    sum(case when e.latency_score = 0 then 1 else 0 end) as latency_spike_count,
    sum(case when e.cost_score = 0 then 1 else 0 end) as cost_spike_count
from {{ ref('stg_agent_runs') }} r
join {{ ref('stg_evaluation_results') }} e on r.run_id = e.run_id
where r.is_duplicate = false
group by cast(r.started_at as date), r.agent_name, r.model_name
