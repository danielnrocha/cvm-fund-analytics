select
    s.capture_id,
    s.source_id
from {{ ref('stg_observations') }} as s
where
    not exists (
        select 1 from {{ ref('captures') }} as c
        where c.capture_id = s.capture_id
    )
