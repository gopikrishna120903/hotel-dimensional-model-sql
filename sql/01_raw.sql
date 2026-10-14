-- Land source extracts as-is into the raw schema (no transformations).
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS dw;
CREATE SCHEMA IF NOT EXISTS mart;

CREATE OR REPLACE TABLE raw.hotels         AS SELECT * FROM read_csv('{raw_dir}/hotels.csv', header = true);
CREATE OR REPLACE TABLE raw.room_types     AS SELECT * FROM read_csv('{raw_dir}/room_types.csv', header = true);
CREATE OR REPLACE TABLE raw.room_inventory AS SELECT * FROM read_csv('{raw_dir}/room_inventory.csv', header = true);
CREATE OR REPLACE TABLE raw.bookings       AS
SELECT * FROM read_csv('{raw_dir}/bookings.csv', header = true,
    columns = {
        'booking_id': 'VARCHAR', 'guest_id': 'VARCHAR', 'hotel_id': 'VARCHAR', 'room_type_code': 'VARCHAR',
        'booking_date': 'DATE', 'check_in_date': 'DATE', 'nights': 'INTEGER', 'channel': 'VARCHAR',
        'rate_plan': 'VARCHAR', 'status': 'VARCHAR', 'nightly_rate': 'DECIMAL(10,2)'
    });
