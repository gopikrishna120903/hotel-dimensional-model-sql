from conftest import scalar


def test_fact_booking_has_one_row_per_source_booking(con):
    assert scalar(con, "SELECT count(*) FROM dw.fact_booking") == scalar(con, "SELECT count(*) FROM raw.bookings")
    assert scalar(con, "SELECT count(*) - count(DISTINCT booking_id) FROM dw.fact_booking") == 0


def test_occupancy_grain_is_hotel_room_type_night(con):
    dupes = scalar(con, """
        SELECT count(*) FROM (
            SELECT date_key, hotel_key, room_type_key FROM dw.fact_daily_occupancy
            GROUP BY ALL HAVING count(*) > 1)""")
    assert dupes == 0
    # 6 hotels x 4 room types x 365 nights
    assert scalar(con, "SELECT count(*) FROM dw.fact_daily_occupancy") == 6 * 4 * 365


def test_no_fact_row_points_to_unknown_members(con):
    unknown = scalar(con, """
        SELECT count(*) FROM dw.fact_booking
        WHERE hotel_key = -1 OR room_type_key = -1 OR guest_key = -1""")
    assert unknown == 0


def test_every_foreign_key_resolves(con):
    orphans = scalar(con, """
        SELECT count(*) FROM dw.fact_booking f
        LEFT JOIN dw.dim_date bd ON bd.date_key = f.booking_date_key
        LEFT JOIN dw.dim_date cd ON cd.date_key = f.check_in_date_key
        LEFT JOIN dw.dim_date od ON od.date_key = f.check_out_date_key
        LEFT JOIN dw.dim_hotel h ON h.hotel_key = f.hotel_key
        LEFT JOIN dw.dim_room_type r ON r.room_type_key = f.room_type_key
        LEFT JOIN dw.dim_guest g ON g.guest_key = f.guest_key
        LEFT JOIN dw.dim_booking_profile p ON p.booking_profile_key = f.booking_profile_key
        WHERE bd.date_key IS NULL OR cd.date_key IS NULL OR od.date_key IS NULL OR h.hotel_key IS NULL
           OR r.room_type_key IS NULL OR g.guest_key IS NULL OR p.booking_profile_key IS NULL""")
    assert orphans == 0


def test_date_dimension_is_contiguous(con):
    gaps = scalar(con, """
        SELECT count(*) FROM (
            SELECT full_date - lag(full_date) OVER (ORDER BY full_date) AS gap FROM dw.dim_date)
        WHERE gap IS NOT NULL AND gap <> 1""")
    assert gaps == 0
