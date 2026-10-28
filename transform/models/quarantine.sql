select capture_id,source_id,period,payload,rejection_reason
from {{ ref('bronze_classified') }} where disposition='rejected'
