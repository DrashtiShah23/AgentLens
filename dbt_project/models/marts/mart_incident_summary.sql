select
    f.primary_category as failure_category,
    f.severity,
    r.agent_name,
    r.prompt_version_id,
    count(*) as incident_count,
    avg(f.confidence_score) as avg_confidence,
    sum(case when f.requires_human_review then 1 else 0 end) as human_review_count,
    max(f.recommendation) as recommended_action
from failure_modes f
join {{ ref('stg_agent_runs') }} r on f.run_id = r.run_id
where r.is_duplicate = false
group by f.primary_category, f.severity, r.agent_name, r.prompt_version_id
