select
    t.tool_name,
    count(*) as call_count,
    {{ safe_divide('sum(case when t.tool_status = \'success\' then 1 else 0 end)', 'count(*)') }} as success_rate,
    {{ safe_divide('sum(case when t.tool_status = \'failed\' then 1 else 0 end)', 'count(*)') }} as error_rate,
    avg(t.latency_ms) as avg_latency_ms
from {{ ref('stg_tool_calls') }} t
group by t.tool_name
