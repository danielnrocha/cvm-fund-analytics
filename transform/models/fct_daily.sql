{{ config(contract={'enforced': true}) }}
select
  sha256(to_json([e.entity_id, cast(c.report_date as varchar)]))::varchar as observation_id,
  e.entity_id::varchar as entity_id,
  e.classification_at_capture::varchar as classification_at_capture,
  c.report_date::date as report_date,
  d.pl::decimal(17,2) as pl,
  (d.subscriptions::decimal(38,2)-d.redemptions::decimal(38,2))::decimal(38,2) as net_flow,
  case when d.entity_id is null then 0 else 1 end::integer as reported,
  1::integer as expected
from {{ ref('entities') }} e
cross join {{ ref('report_calendar') }} c
left join {{ ref('current_daily') }} d on d.entity_id=e.entity_id and d.report_date=c.report_date
