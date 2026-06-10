with source as (
    select * from prompt_versions
),
deduped as (
    select *,
        row_number() over (
            partition by prompt_version_id, agent_name order by loaded_at desc
        ) as rn
    from source
)
select
    prompt_version_id,
    agent_name,
    prompt_name,
    prompt_text,
    cast(created_at as timestamp) as created_at,
    cast(active_flag as boolean) as active_flag,
    change_reason,
    current_timestamp as loaded_at
from deduped
where rn = 1
