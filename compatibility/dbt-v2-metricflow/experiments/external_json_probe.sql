select event_id,
       shipment.id as shipment_id,
       try_cast(shipment.revenue as decimal(18,2)) as revenue,
       case when shipment.revenue is not null
                 and try_cast(shipment.revenue as decimal(18,2)) is null
            then 'invalid_revenue' end as rejection_reason,
       coalesce(array_length(tags), 0) as tag_count
from read_json('fixtures/external-valid.jsonl', format='newline_delimited',
    columns={event_id:'VARCHAR', shipment:'STRUCT(id INTEGER, revenue VARCHAR)', tags:'VARCHAR[]'})
