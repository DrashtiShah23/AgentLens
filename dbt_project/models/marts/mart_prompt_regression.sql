select
    p.prompt_version_id,
    p.agent_name,
    p.change_reason,
    p.active_flag,
    pp.run_count,
    pp.avg_reliability_score as reliability_score,
    pp.failure_rate,
    pp.avg_latency_ms,
    pp.avg_cost_usd,
    case
        when p.prompt_version_id = 'prompt_v5_regression_case'
             and pp.avg_reliability_score < (
                 select avg(avg_reliability_score)
                 from {{ ref('int_prompt_performance') }}
                 where prompt_version_id != 'prompt_v5_regression_case'
             )
        then true else false
    end as regression_detected
from {{ ref('stg_prompt_versions') }} p
join {{ ref('int_prompt_performance') }} pp
    on p.prompt_version_id = pp.prompt_version_id
    and p.agent_name = pp.agent_name
