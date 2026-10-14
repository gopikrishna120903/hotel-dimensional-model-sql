-- Periodic snapshot fact. Grain: one row per hotel, room type, and night.
-- Every night has a row even if nothing was sold, so occupancy averages are correct.
CREATE OR REPLACE TABLE dw.fact_daily_occupancy AS
WITH stay_nights AS (   -- explode each stayed booking into the nights it occupied
    SELECT
        f.hotel_key,
        f.room_type_key,
        CAST(strftime(CAST(n.night AS DATE), '%Y%m%d') AS INTEGER) AS date_key,
        f.nightly_rate
    FROM dw.fact_booking f
    JOIN dw.dim_booking_profile bp USING (booking_profile_key)
    JOIN dw.dim_date ci ON ci.date_key = f.check_in_date_key
    CROSS JOIN LATERAL (
        SELECT unnest(generate_series(ci.full_date, ci.full_date + (f.room_nights - 1) * INTERVAL 1 DAY, INTERVAL 1 DAY)) AS night
    ) n
    WHERE bp.status = 'stayed'
),
calendar AS (           -- every hotel x room type x night in the reporting year
    SELECT h.hotel_key, rt.room_type_key, d.date_key, i.rooms AS rooms_available
    FROM raw.room_inventory i
    JOIN dw.dim_hotel h      ON h.hotel_id = i.hotel_id
    JOIN dw.dim_room_type rt ON rt.room_type_code = i.room_type_code
    CROSS JOIN dw.dim_date d
    WHERE d.year = 2025
)
SELECT
    c.date_key,
    c.hotel_key,
    c.room_type_key,
    c.rooms_available,
    CAST(count(s.date_key) AS INTEGER)                    AS rooms_sold,
    CAST(coalesce(sum(s.nightly_rate), 0) AS DECIMAL(12,2)) AS room_revenue
FROM calendar c
LEFT JOIN stay_nights s
       ON s.hotel_key = c.hotel_key AND s.room_type_key = c.room_type_key AND s.date_key = c.date_key
GROUP BY ALL;
