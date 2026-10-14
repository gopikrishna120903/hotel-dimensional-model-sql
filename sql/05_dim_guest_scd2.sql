-- Guest dimension, SCD Type 2: every change to a tracked attribute
-- (home city, loyalty tier) closes the current row and opens a new version.
CREATE SEQUENCE IF NOT EXISTS dw.guest_key_seq START 1;

CREATE TABLE IF NOT EXISTS dw.dim_guest (
    guest_key     INTEGER PRIMARY KEY,
    guest_id      VARCHAR NOT NULL,
    full_name     VARCHAR,
    email         VARCHAR,
    home_city     VARCHAR,
    loyalty_tier  VARCHAR,
    row_hash      VARCHAR NOT NULL,
    valid_from    DATE NOT NULL,
    valid_to      DATE NOT NULL,
    is_current    BOOLEAN NOT NULL
);

INSERT INTO dw.dim_guest
SELECT -1, 'UNKNOWN', 'Unknown', NULL, 'Unknown', 'Unknown', 'n/a', DATE '1900-01-01', DATE '9999-12-31', TRUE
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_guest WHERE guest_key = -1);
