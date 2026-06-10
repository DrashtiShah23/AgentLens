with source as (
    select * from evaluation_results
),
deduped as (
    select *,
        row_number() over (partition by evaluation_id order by loaded_at desc) as rn
    from source
)
select
    evaluation_id,
    run_id,
    correctness_score,
    sql_score,
    tool_score,
    retrieval_score,
    format_score,
    latency_score,
    cost_score,
    overall_score,
    failure_category,
    severity,
    evaluator_notes,
    cast(evaluated_at as timestamp) as evaluated_at,
    current_timestamp as loaded_at
from deduped
where rn = 1
