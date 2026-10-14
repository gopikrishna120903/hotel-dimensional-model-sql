-- Junk dimension: combines low-cardinality flags (channel, rate plan, status)
-- into one small dimension instead of three tiny ones on the fact table.
CREATE OR REPLACE TABLE dw.dim_booking_profile AS
WITH combos AS (
    SELECT DISTINCT channel, rate_plan, status FROM raw.bookings
)
SELECT
    CAST(row_number() OVER (ORDER BY channel, rate_plan, status) AS INTEGER) AS booking_profile_key,
    channel,
    rate_plan,
    status,
    channel IN ('DIRECT')                 AS is_direct_channel,
    status = 'cancelled'                  AS is_cancelled,
    status = 'stayed'                     AS is_stayed
FROM combos;
