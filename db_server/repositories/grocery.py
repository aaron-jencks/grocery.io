from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Optional

from db_server.db.connection import Database
from db_server.domain.observation import PriceObservation, Sale, Store
from db_server.domain.upc import Product, ProductUnit, ProductVariant
from db_server.domain.commands import PriceObservationInput, SaleInput


class GroceryRepository:
    def __init__(self, database: Database):
        self.database = database

    def list_products(self, updated_after: Optional[str] = None) -> list[Product]:
        with self.database.connect() as connection:
            if updated_after is None:
                rows = connection.execute(
                    """
                    SELECT
                        rowid,
                        name,
                        category,
                        updated_at
                    FROM products
                    ORDER BY name COLLATE NOCASE ASC, rowid ASC
                    """
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT
                        rowid,
                        name,
                        category,
                        updated_at
                    FROM products
                    WHERE updated_at > ?
                    ORDER BY updated_at ASC, rowid ASC
                    """,
                    (updated_after,),
                ).fetchall()

        return [
            Product(
                rowid=row["rowid"],
                name=row["name"],
                category=row["category"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

    def get_catalog_sync_token(self) -> str:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT COALESCE(MAX(updated_at), '') AS sync_token FROM products"
            ).fetchone()
        return str(row["sync_token"])

    def list_variants_for_product(
        self,
        product_name: str,
        updated_after: Optional[str] = None,
    ) -> list[ProductVariant]:
        normalized_name = self._normalize_product_name(product_name)
        with self.database.connect() as connection:
            if updated_after is None:
                rows = connection.execute(
                    """
                    SELECT
                        v.rowid AS variant_id,
                        v.label,
                        v.pack_count,
                        v.net_quantity,
                        v.quantity_unit,
                        v.is_variable_weight,
                        v.upc,
                        v.updated_at AS variant_updated_at,
                        p.rowid AS product_id,
                        p.name AS product_name,
                        p.category AS product_category,
                        p.updated_at AS product_updated_at
                    FROM variants v
                    JOIN products p ON p.rowid = v.product_id
                    WHERE lower(p.name) = ?
                    ORDER BY v.updated_at ASC, v.rowid ASC
                    """,
                    (normalized_name,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT
                        v.rowid AS variant_id,
                        v.label,
                        v.pack_count,
                        v.net_quantity,
                        v.quantity_unit,
                        v.is_variable_weight,
                        v.upc,
                        v.updated_at AS variant_updated_at,
                        p.rowid AS product_id,
                        p.name AS product_name,
                        p.category AS product_category,
                        p.updated_at AS product_updated_at
                    FROM variants v
                    JOIN products p ON p.rowid = v.product_id
                    WHERE lower(p.name) = ?
                      AND v.updated_at > ?
                    ORDER BY v.updated_at ASC, v.rowid ASC
                    """,
                    (normalized_name, updated_after),
                ).fetchall()

        return [self._variant_from_row(row) for row in rows]

    def get_variant_sync_token(self, product_name: str) -> str:
        normalized_name = self._normalize_product_name(product_name)
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT COALESCE(MAX(v.updated_at), '') AS sync_token
                FROM variants v
                JOIN products p ON p.rowid = v.product_id
                WHERE lower(p.name) = ?
                """,
                (normalized_name,),
            ).fetchone()
        return str(row["sync_token"])

    def resolve_upc(self, upc: str) -> Optional[ProductVariant]:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    v.rowid AS variant_id,
                    v.label,
                    v.pack_count,
                    v.net_quantity,
                    v.quantity_unit,
                    v.is_variable_weight,
                    v.upc,
                    v.updated_at AS variant_updated_at,
                    p.rowid AS product_id,
                    p.name AS product_name,
                    p.category AS product_category,
                    p.updated_at AS product_updated_at
                FROM variants v
                JOIN products p ON p.rowid = v.product_id
                WHERE v.upc = ?
                """,
                (upc,),
            ).fetchone()

        if row is None:
            return None

        return self._variant_from_row(row)

    def create_price_observation(self, payload: PriceObservationInput) -> int:
        with self.database.connect() as connection:
            store_id = self._resolve_store_id(connection, payload)
            product_id = self._resolve_product_id(connection, payload)
            variant_id = self._resolve_variant_id(connection, payload, product_id)
            sale_id = self._create_sale(connection, payload.sale) if payload.is_sale else None

            cursor = connection.execute(
                """
                INSERT INTO prices (
                    store_id,
                    variant_id,
                    price_total,
                    observed_at,
                    is_sale,
                    sale_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    store_id,
                    variant_id,
                    payload.price_total,
                    payload.observed_at,
                    int(payload.is_sale),
                    sale_id,
                ),
            )
            return int(cursor.lastrowid)

    def get_price_observation(self, observation_id: int) -> Optional[PriceObservation]:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    pr.rowid AS price_id,
                    pr.price_total,
                    pr.observed_at,
                    pr.is_sale,
                    s.rowid AS store_id,
                    s.name AS store_name,
                    s.address,
                    s.latitude,
                    s.longitude,
                    v.rowid AS variant_id,
                    v.label,
                    v.pack_count,
                    v.net_quantity,
                    v.quantity_unit,
                    v.is_variable_weight,
                    v.upc,
                    p.rowid AS product_id,
                    p.name AS product_name,
                    p.category AS product_category,
                    v.updated_at AS variant_updated_at,
                    p.updated_at AS product_updated_at,
                    sale.rowid AS sale_id,
                    sale.limit_quantity,
                    sale.expiration_date,
                    sale.start_date,
                    sale.minimum_quantity
                FROM prices pr
                JOIN stores s ON s.rowid = pr.store_id
                JOIN variants v ON v.rowid = pr.variant_id
                JOIN products p ON p.rowid = v.product_id
                LEFT JOIN sales sale ON sale.rowid = pr.sale_id
                WHERE pr.rowid = ?
                """,
                (observation_id,),
            ).fetchone()

        if row is None:
            return None

        return PriceObservation(
            rowid=row["price_id"],
            store=Store(
                rowid=row["store_id"],
                name=row["store_name"],
                address=row["address"],
                latitude=row["latitude"],
                longitude=row["longitude"],
            ),
            variant=self._variant_from_row(row),
            price_total=row["price_total"],
            observed_at=dt.datetime.fromisoformat(row["observed_at"]),
            sale=self._sale_from_row(row),
        )

    def _resolve_store_id(
        self,
        connection: sqlite3.Connection,
        payload: PriceObservationInput,
    ) -> int:
        row = connection.execute(
            "SELECT rowid, name FROM stores WHERE address = ?",
            (payload.store_address,),
        ).fetchone()
        if row is not None:
            connection.execute(
                """
                UPDATE stores
                SET name = ?, latitude = ?, longitude = ?
                WHERE rowid = ?
                """,
                (
                    payload.store_name or row["name"],
                    payload.store_latitude,
                    payload.store_longitude,
                    row["rowid"],
                ),
            )
            return int(row["rowid"])

        cursor = connection.execute(
            """
            INSERT INTO stores(name, address, latitude, longitude)
            VALUES (?, ?, ?, ?)
            """,
            (
                payload.store_name,
                payload.store_address,
                payload.store_latitude,
                payload.store_longitude,
            ),
        )
        return int(cursor.lastrowid)

    def _resolve_product_id(
        self,
        connection: sqlite3.Connection,
        payload: PriceObservationInput,
    ) -> int:
        normalized_name = self._normalize_product_name(payload.product_name)
        normalized_category = self._normalize_categories(payload.product_category)
        updated_at = self._utc_now_iso()
        row = connection.execute(
            "SELECT rowid, category FROM products WHERE lower(name) = ?",
            (normalized_name,),
        ).fetchone()
        if row is not None:
            connection.execute(
                "UPDATE products SET name = ?, category = ?, updated_at = ? WHERE rowid = ?",
                (
                    normalized_name,
                    normalized_category or row["category"],
                    updated_at,
                    row["rowid"],
                ),
            )
            return int(row["rowid"])

        cursor = connection.execute(
            "INSERT INTO products(name, category, updated_at) VALUES (?, ?, ?)",
            (normalized_name, normalized_category, updated_at),
        )
        return int(cursor.lastrowid)

    def _resolve_variant_id(
        self,
        connection: sqlite3.Connection,
        payload: PriceObservationInput,
        product_id: int,
    ) -> int:
        row = connection.execute(
            "SELECT rowid, product_id FROM variants WHERE upc = ?",
            (payload.upc,),
        ).fetchone()
        if row is not None:
            if int(row["product_id"]) != product_id:
                raise ValueError("UPC already exists for a different product")
            connection.execute(
                """
                UPDATE variants
                SET label = ?,
                    pack_count = ?,
                    net_quantity = ?,
                    quantity_unit = ?,
                    is_variable_weight = ?,
                    updated_at = ?
                WHERE rowid = ?
                """,
                (
                    payload.variant_label,
                    payload.pack_count,
                    payload.net_quantity,
                    int(payload.quantity_unit.value),
                    int(payload.is_variable_weight),
                    self._utc_now_iso(),
                    row["rowid"],
                ),
            )
            return int(row["rowid"])

        natural_key_row = connection.execute(
            """
            SELECT rowid FROM variants
            WHERE product_id = ?
              AND label = ?
              AND pack_count = ?
              AND net_quantity = ?
              AND quantity_unit = ?
            """,
            (
                product_id,
                payload.variant_label,
                payload.pack_count,
                payload.net_quantity,
                int(payload.quantity_unit.value),
            ),
        ).fetchone()
        if natural_key_row is not None:
            connection.execute(
                """
                UPDATE variants
                SET upc = ?, is_variable_weight = ?, updated_at = ?
                WHERE rowid = ?
                """,
                (
                    payload.upc,
                    int(payload.is_variable_weight),
                    self._utc_now_iso(),
                    natural_key_row["rowid"],
                ),
            )
            return int(natural_key_row["rowid"])

        cursor = connection.execute(
            """
            INSERT INTO variants(
                product_id,
                label,
                pack_count,
                net_quantity,
                quantity_unit,
                is_variable_weight,
                upc,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                payload.variant_label,
                payload.pack_count,
                payload.net_quantity,
                int(payload.quantity_unit.value),
                int(payload.is_variable_weight),
                payload.upc,
                self._utc_now_iso(),
            ),
        )
        return int(cursor.lastrowid)

    def _create_sale(
        self,
        connection: sqlite3.Connection,
        sale: Optional[SaleInput],
    ) -> Optional[int]:
        if sale is None:
            return None

        cursor = connection.execute(
            """
            INSERT INTO sales(limit_quantity, expiration_date, start_date, minimum_quantity)
            VALUES (?, ?, ?, ?)
            """,
            (
                sale.limit_quantity,
                sale.expiration_date,
                sale.start_date,
                sale.minimum_quantity,
            ),
        )
        return int(cursor.lastrowid)

    def _variant_from_row(self, row: sqlite3.Row) -> ProductVariant:
        return ProductVariant(
            rowid=row["variant_id"],
            product=Product(
                rowid=row["product_id"],
                name=row["product_name"],
                category=row["product_category"],
                updated_at=row["product_updated_at"],
            ),
            label=row["label"],
            pack_count=row["pack_count"],
            net_quantity=row["net_quantity"],
            quantity_unit=ProductUnit(row["quantity_unit"]),
            is_variable_weight=bool(row["is_variable_weight"]),
            upc=row["upc"],
            updated_at=row["variant_updated_at"],
        )

    def _sale_from_row(self, row: sqlite3.Row) -> Optional[Sale]:
        if row["sale_id"] is None:
            return None

        expiration_date = row["expiration_date"]
        return Sale(
            rowid=row["sale_id"],
            limit_quantity=row["limit_quantity"],
            expiration_date=(
                dt.datetime.fromisoformat(expiration_date)
                if expiration_date is not None
                else None
            ),
            start_date=dt.datetime.fromisoformat(row["start_date"]),
            minimum_quantity=row["minimum_quantity"],
        )

    def _normalize_categories(self, raw: Optional[str]) -> Optional[str]:
        if raw is None:
            return None

        normalized = "; ".join(
            category.lower()
            for category in dict.fromkeys(
                item.strip()
                for item in raw.split(";")
                if item.strip()
            )
        )
        return normalized or None

    def _normalize_product_name(self, raw: str) -> str:
        normalized = raw.strip().lower()
        if not normalized:
            raise ValueError("Product name is required")
        return normalized

    def _utc_now_iso(self) -> str:
        return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")
