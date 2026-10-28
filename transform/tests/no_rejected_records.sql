select capture_id,source_id,rejection_reason from {{ ref('quarantine') }}
