with counts as (
    select
        capture_id,
        split_part(source_id, ':', 1) as file_sha256,
        count(*) as enveloped,
        count(*) filter (where disposition = 'accepted') as accepted,
        count(*) filter (where disposition = 'rejected') as rejected
    from {{ ref('bronze_classified') }}
    group by 1, 2
)

select
    coalesce(f.capture_id, c.capture_id) as capture_id,
    coalesce(f.file_sha256, c.file_sha256) as file_sha256,
    f.member,
    f.enveloped as declared_enveloped,
    f.excluded,
    coalesce(c.enveloped, 0) as enveloped,
    coalesce(c.accepted, 0) as accepted,
    coalesce(c.rejected, 0) as rejected,
    f.enveloped + f.excluded as source_records,
    (
        f.capture_id is not null and f.excluded >= 0 and f.enveloped >= 0
        and f.enveloped = coalesce(c.enveloped, 0)
        and coalesce(c.enveloped, 0)
        = coalesce(c.accepted, 0) + coalesce(c.rejected, 0)
    ) as balanced
from {{ source('cvm_landing','files') }} as f
full join
    counts as c
    on f.capture_id = c.capture_id and f.file_sha256 = c.file_sha256
