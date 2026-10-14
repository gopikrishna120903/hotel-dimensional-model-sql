-- Transaction fact. Grain: one row per booking.
-- The guest key is resolved "as of" the booking date, so each booking points to
-- the guest version (tier, city) that was true when the booking was made.
CREATE OR REPLACE TABLE dw.fact_booking AS
SELECT
    b.booking_id,                                                             -- degenerate dimension
    CAST(strftime(b.booking_date, '%Y%m%d') AS INTEGER)                        AS booking_date_key,
    CAST(strftime(b.check_in_date, '%Y%m%d') AS INTEGER)                       AS check_in_date_key,
    CAST(strftime(b.check_in_date + b.nights * INTERVAL 1 DAY, '%Y%m%d') AS INTEGER) AS check_out_date_key,
    coalesce(h.hotel_key, -1)                                                  AS hotel_key,
    coalesce(rt.room_type_key, -1)                                             AS room_type_key,
    coalesce(g.guest_key, -1)                                                  AS guest_key,
    bp.booking_profile_key,
    b.nights                                                                   AS room_nights,
    b.nightly_rate,
    date_diff('day', b.booking_date, b.check_in_date)                          AS lead_time_days,
    CAST(CASE b.status
        WHEN 'stayed'  THEN b.nightly_rate * b.nights
        WHEN 'no_show' THEN b.nightly_rate            -- one-night no-show charge
        ELSE 0 END AS DECIMAL(12,2))                                           AS room_revenue,
    CAST(b.nightly_rate * b.nights AS DECIMAL(12,2))                           AS booked_value
FROM raw.bookings b
LEFT JOIN dw.dim_hotel h      ON h.hotel_id = b.hotel_id
LEFT JOIN dw.dim_room_type rt ON rt.room_type_code = b.room_type_code
LEFT JOIN dw.dim_guest g
       ON g.guest_id = b.guest_id
      AND b.booking_date BETWEEN g.valid_from AND g.valid_to
JOIN dw.dim_booking_profile bp
       ON bp.channel = b.channel AND bp.rate_plan = b.rate_plan AND bp.status = b.status;
