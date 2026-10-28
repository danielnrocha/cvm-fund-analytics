select cast(json_extract_string(payload, '$.shipment.id') as integer) as shipment_id,
       cast(json_extract_string(payload, '$.shipment.revenue') as decimal(18,2)) as revenue,
       json_extract_string(payload, '$.shipment.optional') as optional_field
from (select '{"shipment":{"id":5,"revenue":125.50,"tags":["fragile"]}}'::json as payload)
