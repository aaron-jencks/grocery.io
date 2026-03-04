CREATE TABLE IF NOT EXISTS products (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT
);

CREATE INDEX IF NOT EXISTS idx_products_name
    ON products(name);

CREATE TABLE IF NOT EXISTS variants (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    label TEXT NOT NULL,
    pack_count INTEGER NOT NULL,
    net_quantity REAL NOT NULL,
    quantity_unit INTEGER NOT NULL,
    is_variable_weight INTEGER NOT NULL DEFAULT 0,
    upc TEXT NOT NULL UNIQUE,
    FOREIGN KEY(product_id) REFERENCES products(rowid)
);

CREATE INDEX IF NOT EXISTS idx_variants_product_id
    ON variants(product_id);

CREATE TABLE IF NOT EXISTS stores (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    address TEXT NOT NULL UNIQUE,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sales (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    limit_quantity INTEGER,
    expiration_date TEXT,
    start_date TEXT NOT NULL,
    minimum_quantity INTEGER
);

CREATE TABLE IF NOT EXISTS prices (
    rowid INTEGER PRIMARY KEY AUTOINCREMENT,
    store_id INTEGER NOT NULL,
    variant_id INTEGER NOT NULL,
    price_total REAL NOT NULL,
    observed_at TEXT NOT NULL,
    is_sale INTEGER NOT NULL DEFAULT 0,
    sale_id INTEGER,
    FOREIGN KEY(store_id) REFERENCES stores(rowid),
    FOREIGN KEY(variant_id) REFERENCES variants(rowid),
    FOREIGN KEY(sale_id) REFERENCES sales(rowid)
);

CREATE INDEX IF NOT EXISTS idx_prices_variant_id
    ON prices(variant_id);

CREATE INDEX IF NOT EXISTS idx_prices_store_id
    ON prices(store_id);
