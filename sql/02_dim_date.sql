-- Conformed date dimension. Used three times by fact_booking (role-playing:
-- booking date, check-in date, check-out date) and once by fact_daily_occupancy.
CREATE OR REPLACE TABLE dw.dim_date AS
WITH days AS (
    SELECT CAST(d AS DATE) AS full_date
    FROM generate_series(DATE '2024-01-01', DATE '2026-12-31', INTERVAL 1 DAY) AS t(d)
)
SELECT
    CAST(strftime(full_date, '%Y%m%d') AS INTEGER)       AS date_key,
    full_date,
    year(full_date)                                      AS year,
    quarter(full_date)                                   AS quarter,
    month(full_date)                                     AS month,
    strftime(full_date, '%B')                            AS month_name,
    strftime(full_date, '%Y-%m')                         AS year_month,
    dayofmonth(full_date)                                AS day_of_month,
    isodow(full_date)                                    AS iso_day_of_week,
    strftime(full_date, '%A')                            AS day_name,
    -- hotels treat Friday and Saturday nights as the weekend
    isodow(full_date) IN (5, 6)                          AS is_weekend_night,
    CASE WHEN month(full_date) IN (3, 6, 7, 10) THEN 'Peak'
         WHEN month(full_date) IN (1, 2, 8)     THEN 'Low'
         ELSE 'Shoulder' END                             AS season
FROM days;
