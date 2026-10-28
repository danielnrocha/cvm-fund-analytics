select cast(shipment_id as integer) as shipment_id,
cast(shipped_at as date) as shipped_at,
cast(region as varchar) as region,
cast(revenue as decimal(18,2)) as revenue,
cast(cost as decimal(18,2)) as cost
from {{ ref('shipments') }}
