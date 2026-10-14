"""Generate deterministic sample source data for the hotel data warehouse.

Writes CSV extracts that mimic what a property-management system would export:
hotels, room types, room inventory, two guest snapshots (to exercise SCD Type 2),
and bookings. Room capacity is respected so occupancy never exceeds 100%.
"""
from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
YEAR_START = date(2025, 1, 1)
YEAR_END = date(2025, 12, 31)
SNAPSHOT_2_EFFECTIVE = date(2025, 7, 1)

HOTELS = [
    ("H001", "Riverside Dallas", "Dallas", "TX", "Upscale"),
    ("H002", "Uptown Austin", "Austin", "TX", "Upscale"),
    ("H003", "Bayfront Houston", "Houston", "TX", "Midscale"),
    ("H004", "Mile High Denver", "Denver", "CO", "Midscale"),
    ("H005", "Desert Phoenix", "Phoenix", "AZ", "Economy"),
    ("H006", "Lakeshore Chicago", "Chicago", "IL", "Luxury"),
]
ROOM_TYPES = [
    ("STD", "Standard King", 129.0),
    ("DBL", "Standard Double", 139.0),
    ("DLX", "Deluxe", 189.0),
    ("STE", "Suite", 329.0),
]
SEGMENT_MULT = {"Economy": 0.7, "Midscale": 0.9, "Upscale": 1.15, "Luxury": 1.6}
CHANNELS = [("DIRECT", 0.35), ("OTA", 0.40), ("CORPORATE", 0.15), ("GROUP", 0.10)]
RATE_PLANS = ["BAR", "ADVANCE_PURCHASE", "MEMBER", "CORPORATE_NEGOTIATED"]
TIERS = ["None", "Silver", "Gold", "Platinum"]
CITIES = ["Dallas", "Denton", "Austin", "Houston", "Denver", "Chicago", "Phoenix", "Seattle", "Atlanta", "Miami"]
FIRST = ["Ava", "Liam", "Noah", "Emma", "Mia", "Ethan", "Priya", "Arjun", "Sofia", "Lucas", "Zoe", "Ravi", "Maya", "Omar", "Lena"]
LAST = ["Smith", "Patel", "Garcia", "Kim", "Nguyen", "Johnson", "Reddy", "Lopez", "Brown", "Chen", "Davis", "Khan"]


def _write(path: Path, header: list[str], rows: list) -> None:
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def generate(out_dir: Path, n_guests: int = 6000, n_bookings: int = 32000) -> dict[str, int]:
    rng = random.Random(SEED)
    out_dir.mkdir(parents=True, exist_ok=True)

    _write(out_dir / "hotels.csv", ["hotel_id", "hotel_name", "city", "state", "segment"], HOTELS)
    _write(out_dir / "room_types.csv", ["room_type_code", "room_type_name", "base_rate"], ROOM_TYPES)

    inventory = {}
    for h in HOTELS:
        for code, _, _ in ROOM_TYPES:
            ranges = {"STD": (18, 26), "DBL": (12, 18), "DLX": (6, 10), "STE": (2, 4)}
            inventory[(h[0], code)] = rng.randint(*ranges[code])
    _write(out_dir / "room_inventory.csv", ["hotel_id", "room_type_code", "rooms"],
           [(h, r, n) for (h, r), n in inventory.items()])

    # Guest snapshot 1 (effective 2025-01-01)
    guests = []
    for i in range(1, n_guests + 1):
        fn, ln = rng.choice(FIRST), rng.choice(LAST)
        guests.append([f"G{i:05d}", f"{fn} {ln}", f"{fn.lower()}.{ln.lower()}{i}@example.com",
                       rng.choice(CITIES), rng.choices(TIERS, [0.55, 0.25, 0.15, 0.05])[0]])
    _write(out_dir / "guests_snapshot_1.csv", ["guest_id", "full_name", "email", "home_city", "loyalty_tier"], guests)

    # Guest snapshot 2 (effective 2025-07-01): tier upgrades, moves, and new guests
    snap2 = [g[:] for g in guests]
    changed = rng.sample(range(n_guests), 180)
    for idx in changed:
        g = snap2[idx]
        if rng.random() < 0.6 and g[4] != "Platinum":
            g[4] = TIERS[TIERS.index(g[4]) + 1]
        else:
            g[3] = rng.choice([c for c in CITIES if c != g[3]])
    for i in range(n_guests + 1, n_guests + 121):
        fn, ln = rng.choice(FIRST), rng.choice(LAST)
        snap2.append([f"G{i:05d}", f"{fn} {ln}", f"{fn.lower()}.{ln.lower()}{i}@example.com",
                      rng.choice(CITIES), "None"])
    _write(out_dir / "guests_snapshot_2.csv", ["guest_id", "full_name", "email", "home_city", "loyalty_tier"], snap2)

    # Bookings, respecting nightly capacity for non-cancelled bookings
    sold: dict = {}
    seg = {h[0]: h[4] for h in HOTELS}
    base = {r[0]: r[2] for r in ROOM_TYPES}
    rows = []
    attempts = 0
    while len(rows) < n_bookings and attempts < n_bookings * 4:
        attempts += 1
        hotel = rng.choice(HOTELS)[0]
        rt = rng.choices([r[0] for r in ROOM_TYPES], [0.45, 0.30, 0.18, 0.07])[0]
        check_in = YEAR_START + timedelta(days=rng.randint(0, (YEAR_END - YEAR_START).days - 7))
        nights = rng.choices([1, 2, 3, 4, 5, 7], [0.30, 0.28, 0.18, 0.10, 0.08, 0.06])[0]
        lead = min(int(rng.expovariate(1 / 21)), 180)
        booked_on = check_in - timedelta(days=lead)
        # guests can only book once they exist in a snapshot
        pool = len(snap2) if booked_on >= SNAPSHOT_2_EFFECTIVE else n_guests
        guest = f"G{rng.randint(1, pool):05d}"
        channel = rng.choices([c for c, _ in CHANNELS], [w for _, w in CHANNELS])[0]
        plan = "CORPORATE_NEGOTIATED" if channel == "CORPORATE" else rng.choice(RATE_PLANS[:3])
        p_cancel = 0.10 + min(lead, 120) / 120 * 0.20 + (0.08 if channel == "OTA" else 0)
        r = rng.random()
        status = "cancelled" if r < p_cancel else ("no_show" if r < p_cancel + 0.03 else "stayed")
        season = 1.25 if check_in.month in (3, 6, 7, 10) else (0.85 if check_in.month in (1, 2, 8) else 1.0)
        weekend = 1.1 if check_in.weekday() >= 4 else 1.0
        disc = {"ADVANCE_PURCHASE": 0.85, "MEMBER": 0.92, "CORPORATE_NEGOTIATED": 0.88}.get(plan, 1.0)
        rate = round(base[rt] * SEGMENT_MULT[seg[hotel]] * season * weekend * disc * rng.uniform(0.95, 1.05), 2)

        if status != "cancelled":
            nights_list = [check_in + timedelta(days=d) for d in range(nights)]
            if any(sold.get((hotel, rt, n), 0) >= inventory[(hotel, rt)] for n in nights_list):
                continue  # sold out, so the reservation system would reject it
            for n in nights_list:
                sold[(hotel, rt, n)] = sold.get((hotel, rt, n), 0) + 1

        rows.append((f"B{len(rows) + 1:06d}", guest, hotel, rt, booked_on.isoformat(), check_in.isoformat(),
                     nights, channel, plan, status, rate))

    _write(out_dir / "bookings.csv",
           ["booking_id", "guest_id", "hotel_id", "room_type_code", "booking_date", "check_in_date",
            "nights", "channel", "rate_plan", "status", "nightly_rate"], rows)
    return {"guests": len(snap2), "bookings": len(rows), "changed_guests": len(changed)}


if __name__ == "__main__":
    print(generate(Path(__file__).resolve().parents[2] / "data" / "raw"))
