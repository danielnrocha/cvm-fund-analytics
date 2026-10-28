select * from {{ source('cvm_landing', 'registry_cohort') }}
