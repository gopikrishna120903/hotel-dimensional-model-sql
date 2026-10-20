from conftest import scalar


def test_occupancy_never_exceeds_inventory(con):
    assert scalar(con, "SELECT count(*) FROM dw.fact_daily_occupancy WHERE rooms_sold > rooms_available") == 0


def test_stayed_revenue_reconciles_between_the_two_facts(con):
    from_bookings = scalar(con, """
        SELECT sum(f.room_revenue) FROM dw.fact_booking f
        JOIN dw.dim_booking_profile p USING (booking_profile_key) WHERE p.status = 'stayed'""")
    from_nights = scalar(con, "SELECT sum(room_revenue) FROM dw.fact_daily_occupancy")
    assert from_bookings == from_nights


def test_room_nights_reconcile_between_the_two_facts(con):
    from_bookings = scalar(con, """
        SELECT sum(f.room_nights) FROM dw.fact_booking f
        JOIN dw.dim_booking_profile p USING (booking_profile_key) WHERE p.status = 'stayed'""")
    assert from_bookings == scalar(con, "SELECT sum(rooms_sold) FROM dw.fact_daily_occupancy")


def test_cancelled_bookings_carry_no_revenue(con):
    assert scalar(con, """
        SELECT coalesce(sum(f.room_revenue), 0) FROM dw.fact_booking f
        JOIN dw.dim_booking_profile p USING (booking_profile_key) WHERE p.is_cancelled""") == 0


def test_revpar_equals_adr_times_occupancy(con):
    # RevPAR = revenue / available = (revenue / sold) * (sold / available)
    worst = scalar(con, """
        SELECT max(abs(revpar - adr * occupancy_rate)) FROM mart.hotel_monthly_kpis""")
    assert worst < 0.05  # only rounding differences (each KPI is rounded separately)


def test_cancellation_rises_with_lead_time(con):
    rates = dict(con.execute("""
        SELECT lead_time_bucket, sum(bookings * cancellation_rate) / sum(bookings)
        FROM mart.cancellation_by_lead_time GROUP BY lead_time_bucket""").fetchall())
    assert rates["0-7 days"] < rates["8-30 days"] < rates["31-90 days"]


def test_best_month_view_has_one_row_per_hotel(con):
    rows = con.execute("SELECT hotel_name FROM mart.best_month_per_hotel").fetchall()
    assert len(rows) == 6
    assert len({r[0] for r in rows}) == 6


def test_best_month_is_really_the_highest(con):
    better = scalar(con, """
        SELECT count(*) FROM mart.best_month_per_hotel b
        JOIN mart.hotel_monthly_kpis k USING (hotel_name)
        WHERE k.revpar > b.revpar""")
    assert better == 0