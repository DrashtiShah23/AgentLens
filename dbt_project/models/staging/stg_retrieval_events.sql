with source as (
    select * from retrieval_events
),
deduped as (
    select *,
        row_number() over (partition by retrieval_id order by loaded_at desc) as rn
    from source
)
select
    retrieval_id,
    run_id,
    query_text,
    document_id,
    chunk_text,
    rank_position,
    relevance_score,
    cast(was_used_in_answer as boolean) as was_used_in_answer,
    current_timestamp as loaded_at
from deduped
where rn = 1
  and relevance_score between 0 and 1
