{{ config(materialized='incremental', incremental_strategy='append') }}
with incoming as (
  select sha256(to_json([d.capture_id,d.entity_id,cast(d.report_date as varchar)])) as version_id,
    d.*, c.captured_at
  from {{ ref('int_daily') }} d join {{ ref('captures') }} c using(capture_id)
  where not d.conflict
)
select * from incoming i
{% if is_incremental() %}
where not exists(select 1 from {{ this }} old where old.version_id=i.version_id)
{% endif %}
