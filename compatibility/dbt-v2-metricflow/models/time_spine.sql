select cast(d as date) as date_day
from generate_series(date '2026-01-01', date '2026-02-28', interval '1 day') as t(d)
