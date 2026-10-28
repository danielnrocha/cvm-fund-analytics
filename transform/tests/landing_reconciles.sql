select capture_id,file_sha256 from {{ ref('audit_ingestion_files') }} where balanced is distinct from true
