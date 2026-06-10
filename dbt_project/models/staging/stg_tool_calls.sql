with source as (
    select * from tool_calls
),
deduped as (
    select *,
        row_number() over (partition by tool_call_id order by loaded_at desc) as rn
    from source
)
select
    tool_call_id,
    run_id,
    tool_name,
    tool_input,
    tool_output,
    lower(tool_status) as tool_status,
    error_message,
    cast(started_at as timestamp) as started_at,
    cast(completed_at as timestamp) as completed_at,
    latency_ms,
    current_timestamp as loaded_at
from deduped
where rn = 1
