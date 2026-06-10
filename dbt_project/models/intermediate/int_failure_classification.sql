select
    r.run_id,
    r.agent_name,
    r.task_type,
    r.prompt_version_id,
    r.model_name,
    r.started_at,
    e.overall_score,
    f.primary_category as failure_category,
    f.secondary_signals,
    f.confidence_score,
    f.severity,
    f.recommendation,
    f.requires_human_review,
    f.classified_at
from {{ ref('stg_agent_runs') }} r
join {{ ref('stg_evaluation_results') }} e on r.run_id = e.run_id
left join failure_modes f on r.run_id = f.run_id
where r.is_duplicate = false
