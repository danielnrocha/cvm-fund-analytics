select capture_id,source_id,kind,cnpj,subclass,report_date,pl,subscriptions,redemptions,quota,total_assets,investors
from {{ ref('bronze_classified') }} where disposition='accepted'
-- Quality dependencies ensure build skips every business descendant on rejection.
-- depends_on: {{ ref('quarantine') }}
-- depends_on: {{ ref('audit_ingestion_files') }}
-- depends_on: {{ ref('report_calendar') }}
