ALTER TABLE products ADD COLUMN updated_at TEXT;
ALTER TABLE variants ADD COLUMN updated_at TEXT;

UPDATE products
SET updated_at = strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')
WHERE updated_at IS NULL;

UPDATE variants
SET updated_at = strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')
WHERE updated_at IS NULL;
