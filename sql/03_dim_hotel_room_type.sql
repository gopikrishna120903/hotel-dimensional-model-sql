-- Type 1 dimensions with surrogate keys and an "Unknown" member (key -1)
-- so fact rows never carry NULL foreign keys.
CREATE OR REPLACE TABLE dw.dim_hotel AS
SELECT -1 AS hotel_key, 'UNKNOWN' AS hotel_id, 'Unknown' AS hotel_name, 'Unknown' AS city,
       'Unknown' AS state, 'Unknown' AS segment, 0 AS total_rooms
UNION ALL
SELECT CAST(row_number() OVER (ORDER BY hotel_id) AS INTEGER), *
FROM (
    SELECT h.hotel_id, h.hotel_name, h.city, h.state, h.segment, CAST(SUM(i.rooms) AS INTEGER) AS total_rooms
    FROM raw.hotels h
    JOIN raw.room_inventory i USING (hotel_id)
    GROUP BY ALL
);

CREATE OR REPLACE TABLE dw.dim_room_type AS
SELECT -1 AS room_type_key, 'UNK' AS room_type_code, 'Unknown' AS room_type_name,
       CAST(NULL AS DECIMAL(10,2)) AS base_rate, 'Unknown' AS room_class
UNION ALL
SELECT CAST(row_number() OVER (ORDER BY room_type_code) AS INTEGER),
       room_type_code, room_type_name, CAST(base_rate AS DECIMAL(10,2)),
       CASE WHEN room_type_code IN ('DLX', 'STE') THEN 'Premium' ELSE 'Standard' END
FROM raw.room_types;
