UPDATE products
SET
    name = lower(trim(name)),
    category = CASE
        WHEN category IS NULL THEN NULL
        ELSE lower(trim(category))
    END;
