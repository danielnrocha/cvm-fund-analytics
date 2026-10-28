select cast(d as date) as date_day
from generate_series(date '2026-04-01', date '2026-09-30', interval '1 day') t(d)
