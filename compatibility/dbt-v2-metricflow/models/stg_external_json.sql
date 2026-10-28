with parsed as (
    select file_sha256, line_number, payload,
           try_cast(payload as json) as parsed_json
    from {{ source('fixture_landing', 'raw_json_fixture') }}
), typed as (
    select *, json_extract_string(parsed_json, '$.event_id') as event_id,
           try_cast(json_extract_string(parsed_json, '$.shipment.revenue') as decimal(18,2)) as revenue,
           coalesce(json_array_length(parsed_json, '$.tags'), 0) as tag_count
    from parsed
)
select file_sha256, line_number, payload, event_id, revenue, tag_count,
       case when parsed_json is null then 'malformed_json'
            when json_extract_string(parsed_json, '$.shipment.revenue') is not null
                 and revenue is null then 'invalid_revenue'
       end as rejection_reason
from typed
