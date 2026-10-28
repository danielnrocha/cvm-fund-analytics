select * from {{ ref('stg_observations') }}
where capture_id is null or source_id is null or kind is null or cnpj is null or report_date is null
   or pl is null or subscriptions is null or redemptions is null
   or quota is null or total_assets is null or investors is null or investors < 0
