with source as (
    select * from agent_runs
),
deduped as (
    select *,
        row_number() over (partition by run_id order by loaded_at desc) as rn
    from source
)
select
    run_id,
    agent_name,
    lower(task_type) as task_type,
    user_query,
    prompt_version_id,
    model_name,
    cast(started_at as timestamp) as started_at,
    cast(completed_at as timestamp) as completed_at,
    latency_ms,
    input_tokens,
    output_tokens,
    estimated_cost_usd,
    final_answer,
    cast(success_flag as boolean) as success_flag,
    error_message,
    generated_sql,
    expected_answer,
    metadata,
    cast(is_duplicate as boolean) as is_duplicate,
    current_timestamp as loaded_at
from deduped
where rn = 1
