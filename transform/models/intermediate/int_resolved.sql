with registry as (
    select
        cnpj,
        count(*) as candidates,
        min(entity_id) as entity_id
    from {{ ref('entities') }}
    group by cnpj
),

classified as (
    select
        s.*,
        r.entity_id as candidate_id,
        case
            when
                s.kind is null
                or s.kind != 'CLASSES - FIF'
                or s.subclass is not null
                then 'unsupported_level'
            when
                not regexp_full_match(
                    s.cnpj,
                    '[0-9]{14}|[0-9]{2}\.[0-9]{3}\.[0-9]{3}/[0-9]{4}-[0-9]{2}'
                )
                or s.cnpj is null
                then 'invalid_cnpj'
            when r.candidates is null then 'unknown'
            when r.candidates != 1 then 'ambiguous'
            else 'resolved'
        end as identity_status
    from {{ ref('stg_observations') }} as s
    left join
        registry as r
        on regexp_replace(s.cnpj, '[^0-9]', '', 'g') = r.cnpj
)

select
    capture_id,
    source_id,
    kind,
    cnpj,
    subclass,
    report_date,
    pl,
    subscriptions,
    redemptions,
    quota,
    total_assets,
    investors,
    identity_status,
    case when identity_status = 'resolved' then candidate_id end as entity_id
from classified
