with decoded as (
 select *, try_cast(payload as json) as doc
 from {{ source('cvm_landing','raw_envelopes') }}
), fields as (
 select *,
 json_extract_string(doc,'$.data.TP_FUNDO_CLASSE') as kind,
 json_extract_string(doc,'$.data.CNPJ_FUNDO_CLASSE') as cnpj,
 json_extract_string(doc,'$.data.ID_SUBCLASSE') as subclass,
 json_extract_string(doc,'$.data.DT_COMPTC') as date_text,
 json_extract_string(doc,'$.data.VL_PATRIM_LIQ') as pl_text,
 json_extract_string(doc,'$.data.CAPTC_DIA') as subscriptions_text,
 json_extract_string(doc,'$.data.RESG_DIA') as redemptions_text,
 json_extract_string(doc,'$.data.VL_QUOTA') as quota_text,
 json_extract_string(doc,'$.data.VL_TOTAL') as assets_text,
 json_extract_string(doc,'$.data.NR_COTST') as investors_text
 from decoded
), classified as (
 select *, case
 when doc is null then 'malformed_json'
 when json_extract_string(doc,'$.schema_version') is distinct from '1' then 'unsupported_envelope'
 when json_extract_string(doc,'$.error') is not null then json_extract_string(doc,'$.error')
 when kind is null or cnpj is null or date_text is null or pl_text is null
   or subscriptions_text is null or redemptions_text is null or quota_text is null
   or assets_text is null or investors_text is null then 'required_field'
 when not regexp_full_match(cnpj,'[0-9]{14}|[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}') then 'invalid_cnpj'
 when not regexp_full_match(date_text,'[0-9]{4}-[0-9]{2}-[0-9]{2}') or try_cast(date_text as date) is null then 'invalid_date'
 when replace(substr(date_text,1,7),'-','') is distinct from period then 'wrong_period'
 when not regexp_full_match(pl_text,'-?[0-9]{1,15}(\.[0-9]{1,2})?')
   or not regexp_full_match(subscriptions_text,'-?[0-9]{1,15}(\.[0-9]{1,2})?')
   or not regexp_full_match(redemptions_text,'-?[0-9]{1,15}(\.[0-9]{1,2})?')
   or not regexp_full_match(assets_text,'-?[0-9]{1,15}(\.[0-9]{1,2})?')
   or not regexp_full_match(quota_text,'-?[0-9]{1,15}(\.[0-9]{1,12})?') then 'invalid_decimal'
 when not regexp_full_match(investors_text,'[0-9]{1,10}') then 'invalid_investors' end as rejection_reason
 from fields
)
select capture_id,source_id,period,payload,kind,cnpj,subclass,
 try_cast(date_text as date) as report_date,
 try_cast(pl_text as decimal(17,2)) as pl,
 try_cast(subscriptions_text as decimal(17,2)) as subscriptions,
 try_cast(redemptions_text as decimal(17,2)) as redemptions,
 try_cast(quota_text as decimal(27,12)) as quota,
 try_cast(assets_text as decimal(17,2)) as total_assets,
 try_cast(investors_text as bigint) as investors,
 rejection_reason,
 case when rejection_reason is null then 'accepted' else 'rejected' end as disposition
from classified
