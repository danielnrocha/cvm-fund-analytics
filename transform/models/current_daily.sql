select * from {{ ref('sat_daily_report') }}
qualify row_number() over(partition by entity_id, report_date order by captured_at desc, capture_id desc)=1
