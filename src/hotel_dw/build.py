"""Build the hotel data warehouse end to end on DuckDB.

Runs the SQL scripts in order, applies the two guest snapshots through the
SCD Type 2 load, and prints headline KPIs.

    python -m hotel_dw.build                # build into hotel_dw.duckdb
    python -m hotel_dw.build --db :memory:  # throwaway build
"""
from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "sql"
RAW_DIR = ROOT / "data" / "raw"

# (snapshot file, date it takes effect, valid_from used for guests seen for the first time)
GUEST_SNAPSHOTS = [
    ("guests_snapshot_1.csv", "2025-01-01", "1900-01-01"),  # initial load: history starts "forever ago"
    ("guests_snapshot_2.csv", "2025-07-01", "2025-07-01"),
]


def run_script(con: duckdb.DuckDBPyConnection, name: str, **params: str) -> None:
    sql = (SQL_DIR / name).read_text()
    for key, value in params.items():
        sql = sql.replace("{" + key + "}", value)
    con.execute(sql)


def build(db_path: str = str(ROOT / "hotel_dw.duckdb"), raw_dir: Path = RAW_DIR) -> duckdb.DuckDBPyConnection:
    if not (raw_dir / "bookings.csv").exists():
        from hotel_dw.generate_data import generate
        generate(raw_dir)

    if db_path != ":memory:":
        Path(db_path).unlink(missing_ok=True)
    con = duckdb.connect(db_path)
    raw = raw_dir.as_posix()

    run_script(con, "01_raw.sql", raw_dir=raw)
    run_script(con, "02_dim_date.sql")
    run_script(con, "03_dim_hotel_room_type.sql")
    run_script(con, "04_dim_booking_profile.sql")
    run_script(con, "05_dim_guest_scd2.sql")
    for file_name, effective, initial_from in GUEST_SNAPSHOTS:
        run_script(con, "05b_guest_scd2_load.sql",
                   snapshot_file=f"{raw}/{file_name}", effective_date=effective, initial_valid_from=initial_from)
    run_script(con, "06_fact_booking.sql")
    run_script(con, "07_fact_daily_occupancy.sql")
    run_script(con, "08_marts.sql")
    return con


def summary(con: duckdb.DuckDBPyConnection) -> None:
    counts = con.execute("""
        SELECT (SELECT count(*) FROM dw.fact_booking),
               (SELECT count(*) FROM dw.fact_daily_occupancy),
               (SELECT count(*) FROM dw.dim_guest WHERE guest_key > 0),
               (SELECT count(DISTINCT guest_id) FROM dw.dim_guest WHERE guest_key > 0)
    """).fetchone()
    print(f"fact_booking rows:          {counts[0]:,}")
    print(f"fact_daily_occupancy rows:  {counts[1]:,}")
    print(f"dim_guest rows / guests:    {counts[2]:,} / {counts[3]:,}  (SCD2 versions)")
    print("\nFull-year KPIs by hotel:")
    rows = con.execute("""
        SELECT hotel_name,
               round(sum(room_nights_sold) / sum(room_nights_available), 3) AS occupancy,
               round(sum(room_revenue) / sum(room_nights_sold), 2)          AS adr,
               round(sum(room_revenue) / sum(room_nights_available), 2)     AS revpar
        FROM mart.hotel_monthly_kpis GROUP BY hotel_name ORDER BY revpar DESC
    """).fetchall()
    print(f"  {'hotel':<20}{'occupancy':>10}{'ADR':>10}{'RevPAR':>10}")
    for name, occ, adr, revpar in rows:
        print(f"  {name:<20}{occ:>10.1%}{adr:>10.2f}{revpar:>10.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(ROOT / "hotel_dw.duckdb"))
    args = parser.parse_args()
    summary(build(args.db))


if __name__ == "__main__":
    main()
