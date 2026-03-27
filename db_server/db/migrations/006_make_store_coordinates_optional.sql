CREATE TABLE stores_new (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    address TEXT NOT NULL UNIQUE,
    latitude REAL,
    longitude REAL,
    requires_paid_membership INTEGER NOT NULL DEFAULT 0
);

INSERT INTO stores_new (
    rowid,
    name,
    address,
    latitude,
    longitude,
    requires_paid_membership
)
SELECT
    rowid,
    name,
    address,
    latitude,
    longitude,
    requires_paid_membership
FROM stores;

DROP TABLE stores;
ALTER TABLE stores_new RENAME TO stores;
