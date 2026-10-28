select s.* from {{ ref('stg_observations') }} s
where not exists(select 1 from {{ ref('captures') }} c where c.capture_id=s.capture_id)
