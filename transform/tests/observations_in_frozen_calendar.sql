select
    s.capture_id,
    s.source_id,
    s.report_date
from {{ ref('stg_observations') }} as s
where
    not exists (
        select 1 from {{ ref('report_calendar') }} as c
        where c.report_date = s.report_date
    )
