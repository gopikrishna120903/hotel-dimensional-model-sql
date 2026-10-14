-- Apply one guest snapshot to dim_guest as of {effective_date}.
-- Parameters filled in by the build runner: {snapshot_file}, {effective_date}, {initial_valid_from}
CREATE OR REPLACE TEMP TABLE stg_guest AS
SELECT
    guest_id,
    full_name,
    lower(trim(email))                                         AS email,
    home_city,
    loyalty_tier,
    md5(concat_ws('|', coalesce(home_city, ''), coalesce(loyalty_tier, ''))) AS row_hash
FROM read_csv('{snapshot_file}', header = true, all_varchar = true);

-- 1) Close current versions whose tracked attributes changed.
UPDATE dw.dim_guest AS d
SET valid_to   = DATE '{effective_date}' - INTERVAL 1 DAY,
    is_current = FALSE
FROM stg_guest AS s
WHERE d.guest_id = s.guest_id
  AND d.is_current
  AND d.row_hash <> s.row_hash;

-- 2) Overwrite non-tracked attributes in place (Type 1 behaviour for name/email).
UPDATE dw.dim_guest AS d
SET full_name = s.full_name,
    email     = s.email
FROM stg_guest AS s
WHERE d.guest_id = s.guest_id
  AND d.is_current
  AND (d.full_name IS DISTINCT FROM s.full_name OR d.email IS DISTINCT FROM s.email);

-- 3) Open new versions for changed guests and brand-new guests.
INSERT INTO dw.dim_guest
SELECT
    nextval('dw.guest_key_seq'),
    s.guest_id, s.full_name, s.email, s.home_city, s.loyalty_tier, s.row_hash,
    CASE WHEN EXISTS (SELECT 1 FROM dw.dim_guest h WHERE h.guest_id = s.guest_id)
         THEN DATE '{effective_date}'
         ELSE DATE '{initial_valid_from}' END,
    DATE '9999-12-31',
    TRUE
FROM stg_guest AS s
WHERE NOT EXISTS (
    SELECT 1 FROM dw.dim_guest d
    WHERE d.guest_id = s.guest_id AND d.is_current
);
