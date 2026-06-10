select
    cast(f.classified_at as date) as failure_date,
    f.primary_category as failure_category,
    f.severity,
    r.agent_name,
    count(*) as failure_count
from failure_modes f
join {{ ref('stg_agent_runs') }} r on f.run_id = r.run_id
where r.is_duplicate = false
group by cast(f.classified_at as date), f.primary_category, f.severity, r.agent_name
