{{ config(materialized='incremental', incremental_strategy='append') }}
with incoming as (
    select
        sha256(
            to_json([d.capture_id, d.entity_id, cast(d.report_date as varchar)])
        ) as version_id,
        d.capture_id,
        d.entity_id,
        d.report_date,
        d.pl,
        d.subscriptions,
        d.redemptions,
        d.quota,
        d.total_assets,
        d.investors,
        d.source_count,
        d.source_ids,
        d.conflict,
        c.captured_at
    from {{ ref('int_daily') }} as d
    inner join {{ ref('captures') }} as c on d.capture_id = c.capture_id
    where not d.conflict
)

select
    i.version_id,
    i.capture_id,
    i.entity_id,
    i.report_date,
    i.pl,
    i.subscriptions,
    i.redemptions,
    i.quota,
    i.total_assets,
    i.investors,
    i.source_count,
    i.source_ids,
    i.conflict,
    i.captured_at
from incoming as i
{% if is_incremental() %}
    where
        not exists (
            select 1 from {{ this }} as previous
            where previous.version_id = i.version_id
        )
{% endif %}
