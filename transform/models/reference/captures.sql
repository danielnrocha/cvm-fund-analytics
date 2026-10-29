-- Convert absolute microseconds to explicit UTC-naive timestamp without session timezone.
select
    capture_id,
    make_timestamp(epoch_us(captured_at)) as captured_at
from {{ source('cvm_landing', 'captures') }}
