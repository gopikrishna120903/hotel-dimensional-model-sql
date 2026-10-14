from conftest import scalar


def test_exactly_one_current_row_per_guest(con):
    assert scalar(con, """
        SELECT count(*) FROM (
            SELECT guest_id FROM dw.dim_guest WHERE guest_key > 0
            GROUP BY guest_id HAVING sum(CASE WHEN is_current THEN 1 ELSE 0 END) <> 1)""") == 0


def test_versions_never_overlap_or_leave_gaps(con):
    bad = scalar(con, """
        SELECT count(*) FROM (
            SELECT valid_from, lag(valid_to) OVER (PARTITION BY guest_id ORDER BY valid_from) AS prev_to
            FROM dw.dim_guest WHERE guest_key > 0)
        WHERE prev_to IS NOT NULL AND valid_from <> prev_to + INTERVAL 1 DAY""")
    assert bad == 0


def test_changed_guests_get_a_second_version(con):
    # The generator changed 180 guests' tier or home city in snapshot 2.
    assert scalar(con, """
        SELECT count(*) FROM (SELECT guest_id FROM dw.dim_guest WHERE guest_key > 0
                              GROUP BY guest_id HAVING count(*) = 2)""") == 180


def test_name_or_email_change_alone_does_not_create_a_version(con):
    # Only tracked attributes (home_city, loyalty_tier) drive the row hash.
    assert scalar(con, """
        SELECT count(*) FROM (
            SELECT guest_id, row_hash FROM dw.dim_guest WHERE guest_key > 0
            GROUP BY ALL HAVING count(*) > 1)""") == 0


def test_bookings_use_the_guest_version_valid_on_the_booking_date(con):
    mismatches = scalar(con, """
        SELECT count(*) FROM dw.fact_booking f
        JOIN dw.dim_guest g USING (guest_key)
        JOIN dw.dim_date d ON d.date_key = f.booking_date_key
        WHERE d.full_date NOT BETWEEN g.valid_from AND g.valid_to""")
    assert mismatches == 0
    # and at least some bookings landed on each side of the change
    assert scalar(con, """
        SELECT count(DISTINCT g.is_current) FROM dw.fact_booking f JOIN dw.dim_guest g USING (guest_key)
        WHERE g.guest_id IN (SELECT guest_id FROM dw.dim_guest GROUP BY guest_id HAVING count(*) = 2)""") == 2
