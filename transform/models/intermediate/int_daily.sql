select
    capture_id,
    entity_id,
    report_date,
    min(pl) as pl,
    min(subscriptions) as subscriptions,
    min(redemptions) as redemptions,
    min(quota) as quota,
    min(total_assets) as total_assets,
    min(investors) as investors,
    count(distinct source_id) as source_count,
    string_agg(distinct source_id, '|' order by source_id) as source_ids,
    -- DuckDB row-value DISTINCT requires tuple parentheses (ST08 false positive).
    count(distinct(pl, subscriptions, redemptions, quota, total_assets, investors)) > 1 as conflict -- noqa: ST08,RF04,LT05
from {{ ref('int_resolved') }}
where identity_status = 'resolved'
group by capture_id, entity_id, report_date
