-- Business-facing views on top of the star schema.

-- Core hotel KPIs by month: occupancy, ADR (average daily rate), RevPAR (revenue per available room).
CREATE OR REPLACE VIEW mart.hotel_monthly_kpis AS
SELECT
    h.hotel_name,
    h.segment,
    d.year_month,
    sum(o.rooms_available)                                              AS room_nights_available,
    sum(o.rooms_sold)                                                   AS room_nights_sold,
    sum(o.room_revenue)                                                 AS room_revenue,
    round(sum(o.rooms_sold) / sum(o.rooms_available), 4)                AS occupancy_rate,
    round(sum(o.room_revenue) / nullif(sum(o.rooms_sold), 0), 2)        AS adr,
    round(sum(o.room_revenue) / sum(o.rooms_available), 2)              AS revpar
FROM dw.fact_daily_occupancy o
JOIN dw.dim_hotel h USING (hotel_key)
JOIN dw.dim_date d  USING (date_key)
GROUP BY ALL;

-- Month-over-month RevPAR change per hotel (window function).
CREATE OR REPLACE VIEW mart.hotel_revpar_trend AS
SELECT
    hotel_name,
    year_month,
    revpar,
    lag(revpar) OVER (PARTITION BY hotel_name ORDER BY year_month)       AS prev_month_revpar,
    round(revpar / nullif(lag(revpar) OVER (PARTITION BY hotel_name ORDER BY year_month), 0) - 1, 4) AS mom_change
FROM mart.hotel_monthly_kpis;

-- Cancellation rate by booking lead-time bucket and channel.
CREATE OR REPLACE VIEW mart.cancellation_by_lead_time AS
SELECT
    bp.channel,
    CASE WHEN f.lead_time_days <= 7  THEN '0-7 days'
         WHEN f.lead_time_days <= 30 THEN '8-30 days'
         WHEN f.lead_time_days <= 90 THEN '31-90 days'
         ELSE '90+ days' END                                            AS lead_time_bucket,
    count(*)                                                            AS bookings,
    round(avg(CASE WHEN bp.is_cancelled THEN 1 ELSE 0 END), 4)          AS cancellation_rate
FROM dw.fact_booking f
JOIN dw.dim_booking_profile bp USING (booking_profile_key)
GROUP BY ALL;

-- Channel mix: share of realized revenue by booking channel.
CREATE OR REPLACE VIEW mart.channel_mix AS
SELECT
    bp.channel,
    count(*) FILTER (WHERE bp.is_stayed)                                AS stays,
    sum(f.room_revenue)                                                 AS room_revenue,
    round(sum(f.room_revenue) / sum(sum(f.room_revenue)) OVER (), 4)    AS revenue_share
FROM dw.fact_booking f
JOIN dw.dim_booking_profile bp USING (booking_profile_key)
GROUP BY ALL;

-- Revenue by loyalty tier as it was at booking time (made possible by SCD Type 2).
CREATE OR REPLACE VIEW mart.revenue_by_loyalty_tier AS
SELECT
    g.loyalty_tier,
    count(DISTINCT g.guest_id)                                          AS guests,
    count(*)                                                            AS bookings,
    sum(f.room_revenue)                                                 AS room_revenue,
    round(sum(f.room_revenue) / count(DISTINCT g.guest_id), 2)          AS revenue_per_guest
FROM dw.fact_booking f
JOIN dw.dim_guest g USING (guest_key)
GROUP BY ALL;

-- Repeat-guest rate per hotel: share of guests with 2+ stays.
CREATE OR REPLACE VIEW mart.repeat_guest_rate AS
WITH stays AS (
    SELECT h.hotel_name, g.guest_id, count(*) AS stays
    FROM dw.fact_booking f
    JOIN dw.dim_booking_profile bp USING (booking_profile_key)
    JOIN dw.dim_guest g USING (guest_key)
    JOIN dw.dim_hotel h USING (hotel_key)
    WHERE bp.is_stayed
    GROUP BY ALL
)
SELECT hotel_name,
       count(*)                                         AS guests,
       count(*) FILTER (WHERE stays >= 2)               AS repeat_guests,
       round(count(*) FILTER (WHERE stays >= 2) / count(*), 4) AS repeat_rate
FROM stays
GROUP BY hotel_name;

-- Each hotel's best month by RevPAR.
CREATE OR REPLACE VIEW mart.best_month_per_hotel AS
SELECT hotel_name, year_month, occupancy_rate, adr, revpar
FROM (
    SELECT *,
           row_number() OVER (PARTITION BY hotel_name ORDER BY revpar DESC) AS rn
    FROM mart.hotel_monthly_kpis
)
WHERE rn = 1;
