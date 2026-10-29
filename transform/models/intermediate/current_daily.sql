select
    version_id,
    capture_id,
    entity_id,
    report_date,
    pl,
    subscriptions,
    redemptions,
    quota,
    total_assets,
    investors,
    source_count,
    source_ids,
    conflict,
    captured_at
from {{ ref('sat_daily_report') }}
qualify
    row_number()
        over (
            partition by entity_id, report_date
            order by captured_at desc, capture_id desc
        )
    = 1
