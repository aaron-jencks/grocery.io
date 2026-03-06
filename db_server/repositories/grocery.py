from __future__ import annotations

import datetime as dt
import sqlite3
from dataclasses import dataclass
from typing import Optional

from db_server.db.connection import Database
from db_server.domain.observation import PriceObservation, Sale, Store
from db_server.domain.upc import Product, ProductUnit, ProductVariant
from db_server.domain.commands import PriceObservationInput, SaleInput


@dataclass(frozen=True)
class ShoppingOptimizationInput:
    item_id: int
    product_name: str
    desired_count: int
    comparison_mode: str
    preferred_upc: Optional[str]


@dataclass(frozen=True)
class ShoppingOptimizationMatch:
    item_id: int
    comparison_mode: str
    desired_count: int
    store_id: int
    store_name: Optional[str]
    store_address: str
    store_latitude: float
    store_longitude: float
    upc: str
    product_name: str
    variant_label: str
    pack_count: int
    net_quantity: float
    quantity_unit: ProductUnit
    price_observation_id: int
    observed_price_total: float
    observed_at: str
    estimated_total_price: float


@dataclass(frozen=True)
class ShoppingOptimizationUnmatched:
    item_id: int
    product_name: str
    reason: str


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

    def optimize_grocery_list(
        self,
        items: list[ShoppingOptimizationInput],
    ) -> tuple[list[ShoppingOptimizationMatch], list[ShoppingOptimizationUnmatched]]:
        matches: list[ShoppingOptimizationMatch] = []
        unmatched: list[ShoppingOptimizationUnmatched] = []
        for item in items:
            match, reason = self._find_best_match_for_item(item)
            if match is None:
                unmatched.append(
                    ShoppingOptimizationUnmatched(
                        item_id=item.item_id,
                        product_name=item.product_name,
                        reason=reason or "No price information available",
                    )
                )
            else:
                matches.append(match)
                if reason is not None:
                    unmatched.append(
                        ShoppingOptimizationUnmatched(
                            item_id=item.item_id,
                            product_name=item.product_name,
                            reason=f"Warning: {reason}",
                        )
                    )
        return matches, unmatched

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

    def _find_best_match_for_item(
        self,
        item: ShoppingOptimizationInput,
    ) -> tuple[Optional[ShoppingOptimizationMatch], Optional[str]]:
        desired_count = max(1, item.desired_count)
        with self.database.connect() as connection:
            if item.preferred_upc:
                rows = connection.execute(
                    """
                    SELECT
                        pr.rowid AS price_observation_id,
                        pr.price_total,
                        pr.observed_at,
                        s.rowid AS store_id,
                        s.name AS store_name,
                        s.address AS store_address,
                        s.latitude AS store_latitude,
                        s.longitude AS store_longitude,
                        v.rowid AS variant_id,
                        v.label AS variant_label,
                        v.pack_count,
                        v.net_quantity,
                        v.quantity_unit,
                        v.upc,
                        p.name AS product_name
                    FROM prices pr
                    JOIN stores s ON s.rowid = pr.store_id
                    JOIN variants v ON v.rowid = pr.variant_id
                    JOIN products p ON p.rowid = v.product_id
                    WHERE v.upc = ?
                    """,
                    (item.preferred_upc,),
                ).fetchall()
            else:
                rows = connection.execute(
                    """
                    SELECT
                        pr.rowid AS price_observation_id,
                        pr.price_total,
                        pr.observed_at,
                        s.rowid AS store_id,
                        s.name AS store_name,
                        s.address AS store_address,
                        s.latitude AS store_latitude,
                        s.longitude AS store_longitude,
                        v.rowid AS variant_id,
                        v.label AS variant_label,
                        v.pack_count,
                        v.net_quantity,
                        v.quantity_unit,
                        v.upc,
                        p.name AS product_name
                    FROM prices pr
                    JOIN stores s ON s.rowid = pr.store_id
                    JOIN variants v ON v.rowid = pr.variant_id
                    JOIN products p ON p.rowid = v.product_id
                    WHERE lower(p.name) = ?
                    """,
                    (self._normalize_product_name(item.product_name),),
                ).fetchall()

        if not rows:
            return None, "No price information available"

        target_dimension: Optional[str] = None
        fallback_warning: Optional[str] = None
        if item.comparison_mode == "best_unit_value":
            target_dimension = self._resolve_target_dimension(rows)
            if target_dimension is None:
                fallback_warning = (
                    "Used approximate per-unit comparison across non-comparable units. "
                    "Results may be suboptimal."
                )

        best_row = None
        best_score = None
        for row in rows:
            pack_count = int(row["pack_count"]) if row["pack_count"] else 1
            price_total = float(row["price_total"])
            if pack_count <= 0:
                continue

            if item.comparison_mode == "best_unit_value":
                net_quantity = float(row["net_quantity"])
                if net_quantity <= 0:
                    continue
                if target_dimension is None:
                    score = price_total / (pack_count * net_quantity)
                else:
                    converted_quantity = self._convert_quantity(
                        net_quantity=net_quantity,
                        unit=ProductUnit(int(row["quantity_unit"])),
                        target_dimension=target_dimension,
                    )
                    if converted_quantity is None or converted_quantity <= 0:
                        continue
                    score = price_total / (pack_count * converted_quantity)
            else:
                score = price_total / pack_count

            observed_at = row["observed_at"]
            if (
                best_row is None
                or score < best_score
                or (score == best_score and observed_at > best_row["observed_at"])
            ):
                best_row = row
                best_score = score

        if best_row is None:
            if item.comparison_mode == "best_unit_value":
                return (
                    None,
                    "No comparable unit-convertible price information available.",
                )
            return None, "No price information available"

        selected_pack = int(best_row["pack_count"]) if best_row["pack_count"] else 1
        estimated_total = float(best_row["price_total"]) * desired_count / max(1, selected_pack)
        return (
            ShoppingOptimizationMatch(
                item_id=item.item_id,
                comparison_mode=item.comparison_mode,
                desired_count=desired_count,
                store_id=int(best_row["store_id"]),
                store_name=best_row["store_name"],
                store_address=best_row["store_address"],
                store_latitude=float(best_row["store_latitude"]),
                store_longitude=float(best_row["store_longitude"]),
                upc=best_row["upc"],
                product_name=best_row["product_name"],
                variant_label=best_row["variant_label"],
                pack_count=int(best_row["pack_count"]),
                net_quantity=float(best_row["net_quantity"]),
                quantity_unit=ProductUnit(int(best_row["quantity_unit"])),
                price_observation_id=int(best_row["price_observation_id"]),
                observed_price_total=float(best_row["price_total"]),
                observed_at=best_row["observed_at"],
                estimated_total_price=estimated_total,
            ),
            fallback_warning,
        )

    def _resolve_target_dimension(self, rows: list[sqlite3.Row]) -> Optional[str]:
        candidate_dimensions: list[set[str]] = []
        for row in rows:
            unit = ProductUnit(int(row["quantity_unit"]))
            candidate_dimensions.append(self._unit_dimensions(unit))
        if not candidate_dimensions:
            return None

        common = set(candidate_dimensions[0])
        for dimensions in candidate_dimensions[1:]:
            common &= dimensions
        if len(common) == 1:
            return next(iter(common))
        if len(common) > 1:
            return "mass"
        return None

    def _unit_dimensions(self, unit: ProductUnit) -> set[str]:
        if unit == ProductUnit.EA:
            return {"count"}
        if unit in {ProductUnit.LB, ProductUnit.KG, ProductUnit.G}:
            return {"mass"}
        if unit in {
            ProductUnit.LIT,
            ProductUnit.ML,
            ProductUnit.GAL,
            ProductUnit.QT,
            ProductUnit.PT,
            ProductUnit.TSP,
            ProductUnit.TBSP,
        }:
            return {"volume"}
        if unit == ProductUnit.OZ:
            return {"mass", "volume"}
        return set()

    def _convert_quantity(
        self,
        net_quantity: float,
        unit: ProductUnit,
        target_dimension: str,
    ) -> Optional[float]:
        if target_dimension == "count":
            return net_quantity if unit == ProductUnit.EA else None
        if target_dimension == "mass":
            factor = self._mass_factor(unit)
            return net_quantity * factor if factor is not None else None
        if target_dimension == "volume":
            factor = self._volume_factor(unit)
            return net_quantity * factor if factor is not None else None
        return None

    def _mass_factor(self, unit: ProductUnit) -> Optional[float]:
        if unit == ProductUnit.G:
            return 1.0
        if unit == ProductUnit.KG:
            return 1000.0
        if unit == ProductUnit.LB:
            return 453.59237
        if unit == ProductUnit.OZ:
            return 28.349523125
        return None

    def _volume_factor(self, unit: ProductUnit) -> Optional[float]:
        if unit == ProductUnit.ML:
            return 1.0
        if unit == ProductUnit.LIT:
            return 1000.0
        if unit == ProductUnit.GAL:
            return 3785.411784
        if unit == ProductUnit.QT:
            return 946.352946
        if unit == ProductUnit.PT:
            return 473.176473
        if unit == ProductUnit.TSP:
            return 4.92892159375
        if unit == ProductUnit.TBSP:
            return 14.78676478125
        if unit == ProductUnit.OZ:
            return 29.5735295625
        return None

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
