{{ config(contract={'enforced': true}) }}
select cast(shipment_id as integer) as shipment_id,
       cast(revenue - cost as decimal(18,2)) as profit
from {{ ref('fct_shipments') }}
