{{ config(materialized='incremental', incremental_strategy='delete+insert', unique_key='shipment_id') }}
select shipment_id, revenue from {{ ref('fct_shipments') }}
