-- A repeated version key must have the same business payload and source set.
select
    d.capture_id,
    d.entity_id,
    d.report_date
from {{ ref('int_daily') }} as d
inner join {{ ref('sat_daily_report') }} as s
    on
        d.capture_id = s.capture_id
        and d.entity_id = s.entity_id
        and d.report_date = s.report_date
inner join {{ ref('captures') }} as c on d.capture_id = c.capture_id
where
    (
        d.pl,
        d.subscriptions,
        d.redemptions,
        d.quota,
        d.total_assets,
        d.investors,
        d.source_ids,
        c.captured_at
    )
    is distinct from (
        s.pl,
        s.subscriptions,
        s.redemptions,
        s.quota,
        s.total_assets,
        s.investors,
        s.source_ids,
        s.captured_at
    )
