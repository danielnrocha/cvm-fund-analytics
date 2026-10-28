select cast(account_id as varchar) || ':' || cast(balance_date as varchar) as balance_id,
       cast(account_id as varchar) as account_id,
       cast(balance_date as date) as balance_date,
       cast(balance as decimal(18,2)) as balance
from {{ ref('balances') }}
