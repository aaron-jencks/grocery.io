from __future__ import annotations

import datetime as dt
import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from db_server.db.connection import Database
from db_server.domain.observation import PriceObservation, Sale, Store
from db_server.domain.upc import PackagingStyle, Product, ProductUnit, ProductVariant
from db_server.domain.commands import PriceObservationInput, SaleInput


@dataclass(frozen=True)
class ShoppingOptimizationInput:
    item_id: int
    product_name: str
    desired_count: float
    desired_quantity_unit: ProductUnit
    comparison_mode: str
    preferred_upc: Optional[str]
    allow_paid_membership_required: bool = True
    allow_loyalty_card_required: bool = True
    single_store_only: bool = False


@dataclass(frozen=True)
class ShoppingOptimizationMatch:
    item_id: int
    comparison_mode: str
    desired_count: float
    store_id: int
    store_name: Optional[str]
    store_address: str
    store_latitude: Optional[float]
    store_longitude: Optional[float]
    store_requires_paid_membership: bool
    upc: str
    product_name: str
    variant_label: str
    variant_brand: Optional[str]
    variant_flavor: Optional[str]
    variant_packaging_style: Optional[PackagingStyle]
    pack_count: int
    net_quantity: float
    quantity_unit: ProductUnit
    price_observation_id: int
    observed_price_total: float
    observed_at: str
    estimated_total_price: float
    requires_paid_membership: bool
    requires_loyalty_card: bool
    pricing_basis_line: Optional[str] = None
    pricing_equation_line: Optional[str] = None
    approximation_warning: Optional[str] = None


@dataclass(frozen=True)
class ShoppingOptimizationUnmatched:
    item_id: int
    product_name: str
    reason: str


@dataclass(frozen=True)
class CanonicalQuantity:
    dimension: str
    quantity: float


@dataclass(frozen=True)
class EffectivePriceSource:
    row: sqlite3.Row
    is_sale: bool
    unit_price: float
    minimum_quantity: Optional[int]
    limit_quantity: Optional[int]
    multiple_of: Optional[int]
    requires_paid_membership: bool
    requires_loyalty_card: bool


@dataclass(frozen=True)
class CandidatePlan:
    row: sqlite3.Row
    item: ShoppingOptimizationInput
    estimated_total_price: float
    total_supplied_quantity: float
    unit_value_score: float
    total_observation_units: int
    sale_units: int
    non_sale_units: int
    requires_paid_membership: bool
    requires_loyalty_card: bool
    pricing_basis_line: Optional[str]
    pricing_equation_line: Optional[str]
    approximation_warning: Optional[str]


class GroceryRepository:
    def __init__(self, database: Database):
        self.database = database

    def find_store_by_address(self, address: str) -> Optional[Store]:
        normalized_address = address.strip()
        if not normalized_address:
            return None
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    rowid,
                    name,
                    address,
                    latitude,
                    longitude,
                    requires_paid_membership
                FROM stores
                WHERE address = ?
                """,
                (normalized_address,),
            ).fetchone()
        if row is None:
            return None
        return Store(
            rowid=int(row["rowid"]),
            name=row["name"],
            address=row["address"],
            latitude=float(row["latitude"]) if row["latitude"] is not None else None,
            longitude=float(row["longitude"]) if row["longitude"] is not None else None,
            requires_paid_membership=bool(row["requires_paid_membership"]),
        )

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
                        v.brand,
                        v.flavor,
                        v.packaging_style,
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
                        v.brand,
                        v.flavor,
                        v.packaging_style,
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
                    v.brand,
                    v.flavor,
                    v.packaging_style,
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
                    s.requires_paid_membership,
                    v.rowid AS variant_id,
                    v.label,
                    v.brand,
                    v.flavor,
                    v.packaging_style,
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
                    sale.minimum_quantity,
                    sale.multiple_of,
                    sale.requires_paid_membership AS sale_requires_paid_membership,
                    sale.requires_loyalty_card AS sale_requires_loyalty_card
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
                latitude=float(row["latitude"]) if row["latitude"] is not None else None,
                longitude=float(row["longitude"]) if row["longitude"] is not None else None,
                requires_paid_membership=bool(row["requires_paid_membership"]),
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
        candidates_by_item: dict[int, list[CandidatePlan]] = {}

        for item in items:
            candidates, reason = self._find_candidate_plans_for_item(item)
            if not candidates:
                unmatched.append(
                    ShoppingOptimizationUnmatched(
                        item_id=item.item_id,
                        product_name=item.product_name,
                        reason=reason or "No price information available",
                    )
                )
                continue
            candidates_by_item[item.item_id] = candidates

        single_store_requested = any(item.single_store_only for item in items)
        if single_store_requested:
            best_store_id = self._select_best_single_store(candidates_by_item)
            if best_store_id is None:
                for item in items:
                    if item.item_id not in candidates_by_item:
                        continue
                    unmatched.append(
                        ShoppingOptimizationUnmatched(
                            item_id=item.item_id,
                            product_name=item.product_name,
                            reason="No qualifying option at a single store.",
                        )
                    )
                return matches, unmatched

            for item in items:
                item_candidates = candidates_by_item.get(item.item_id)
                if not item_candidates:
                    continue
                store_candidate = next((candidate for candidate in item_candidates if int(candidate.row["store_id"]) == best_store_id), None)
                if store_candidate is None:
                    unmatched.append(
                        ShoppingOptimizationUnmatched(
                            item_id=item.item_id,
                            product_name=item.product_name,
                            reason="No qualifying option at selected store.",
                        )
                    )
                    continue
                matches.append(self._candidate_to_match(store_candidate))
            return matches, unmatched

        for item in items:
            item_candidates = candidates_by_item.get(item.item_id)
            if not item_candidates:
                continue
            matches.append(self._candidate_to_match(item_candidates[0]))

        return matches, unmatched

    def _resolve_store_id(
        self,
        connection: sqlite3.Connection,
        payload: PriceObservationInput,
    ) -> int:
        row = connection.execute(
            "SELECT rowid, name, latitude, longitude FROM stores WHERE address = ?",
            (payload.store_address,),
        ).fetchone()
        if row is not None:
            connection.execute(
                """
                UPDATE stores
                SET name = ?, latitude = ?, longitude = ?, requires_paid_membership = ?
                WHERE rowid = ?
                """,
                (
                    payload.store_name or row["name"],
                    payload.store_latitude if payload.store_latitude is not None else row["latitude"],
                    payload.store_longitude if payload.store_longitude is not None else row["longitude"],
                    int(payload.store_requires_paid_membership),
                    row["rowid"],
                ),
            )
            return int(row["rowid"])

        cursor = connection.execute(
            """
            INSERT INTO stores(name, address, latitude, longitude, requires_paid_membership)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload.store_name,
                payload.store_address,
                payload.store_latitude,
                payload.store_longitude,
                int(payload.store_requires_paid_membership),
            ),
        )
        return int(cursor.lastrowid)

    def _find_best_match_for_item(
        self,
        item: ShoppingOptimizationInput,
    ) -> tuple[Optional[ShoppingOptimizationMatch], Optional[str]]:
        candidates, reason = self._find_candidate_plans_for_item(item)
        if not candidates:
            return None, reason
        return self._candidate_to_match(candidates[0]), None

    def _find_candidate_plans_for_item(
        self,
        item: ShoppingOptimizationInput,
    ) -> tuple[list[CandidatePlan], Optional[str]]:
        desired_count = float(item.desired_count)
        if desired_count <= 0:
            return [], "Desired quantity must be greater than zero."
        requested_quantity = self._to_canonical_quantity(desired_count, item.desired_quantity_unit)
        if requested_quantity is None:
            return [], "Requested quantity unit is not supported."

        with self.database.connect() as connection:
            if item.preferred_upc and item.comparison_mode == "cheapest_price":
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
                        s.requires_paid_membership AS store_requires_paid_membership,
                        v.rowid AS variant_id,
                        v.label AS variant_label,
                        v.brand AS variant_brand,
                        v.flavor AS variant_flavor,
                        v.packaging_style AS variant_packaging_style,
                        v.pack_count,
                        v.net_quantity,
                        v.quantity_unit,
                        v.is_variable_weight,
                        v.upc,
                        p.name AS product_name,
                        pr.is_sale,
                        sale.requires_paid_membership AS sale_requires_paid_membership,
                        sale.requires_loyalty_card AS sale_requires_loyalty_card,
                        sale.minimum_quantity,
                        sale.limit_quantity,
                        sale.multiple_of,
                        sale.start_date,
                        sale.expiration_date
                    FROM prices pr
                    JOIN stores s ON s.rowid = pr.store_id
                    JOIN variants v ON v.rowid = pr.variant_id
                    JOIN products p ON p.rowid = v.product_id
                    LEFT JOIN sales sale ON sale.rowid = pr.sale_id
                    WHERE v.upc = ?
                    ORDER BY pr.observed_at DESC
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
                        s.requires_paid_membership AS store_requires_paid_membership,
                        v.rowid AS variant_id,
                        v.label AS variant_label,
                        v.brand AS variant_brand,
                        v.flavor AS variant_flavor,
                        v.packaging_style AS variant_packaging_style,
                        v.pack_count,
                        v.net_quantity,
                        v.quantity_unit,
                        v.is_variable_weight,
                        v.upc,
                        p.name AS product_name,
                        pr.is_sale,
                        sale.requires_paid_membership AS sale_requires_paid_membership,
                        sale.requires_loyalty_card AS sale_requires_loyalty_card,
                        sale.minimum_quantity,
                        sale.limit_quantity,
                        sale.multiple_of,
                        sale.start_date,
                        sale.expiration_date
                    FROM prices pr
                    JOIN stores s ON s.rowid = pr.store_id
                    JOIN variants v ON v.rowid = pr.variant_id
                    JOIN products p ON p.rowid = v.product_id
                    LEFT JOIN sales sale ON sale.rowid = pr.sale_id
                    WHERE lower(p.name) = ?
                    ORDER BY pr.observed_at DESC
                    """,
                    (self._normalize_product_name(item.product_name),),
                ).fetchall()

        if not rows:
            return [], "No price information available"

        filtered_rows = self._apply_preferred_variant_filter(item, rows)
        if not filtered_rows:
            return [], "No matching preferred variant information available."
        eligible_rows = [
            row for row in filtered_rows
            if (
                item.allow_paid_membership_required
                or not (
                    bool(row["store_requires_paid_membership"])
                    or bool(row["sale_requires_paid_membership"])
                )
            )
            and (
                item.allow_loyalty_card_required
                or not bool(row["sale_requires_loyalty_card"])
            )
        ]
        if not eligible_rows:
            return [], "No price information available"
        best_value_dimension = (
            self._resolve_target_dimension(eligible_rows)
            if item.comparison_mode == "best_unit_value" and item.desired_quantity_unit == ProductUnit.EA
            else None
        )
        if best_value_dimension == "count":
            best_value_dimension = None

        grouped: dict[tuple[int, int], list[sqlite3.Row]] = defaultdict(list)
        for row in eligible_rows:
            grouped[(int(row["store_id"]), int(row["variant_id"]))].append(row)

        candidates: list[CandidatePlan] = []
        for group_rows in grouped.values():
            candidates.extend(
                self._candidate_plans_for_group(
                    item,
                    requested_quantity,
                    group_rows,
                    best_value_dimension=best_value_dimension,
                )
            )

        if not candidates:
            return [], "No price option could satisfy the requested quantity."

        candidates.sort(key=self._candidate_sort_key)
        return candidates, None

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

    def _apply_preferred_variant_filter(
        self,
        item: ShoppingOptimizationInput,
        rows: list[sqlite3.Row],
    ) -> list[sqlite3.Row]:
        if not item.preferred_upc:
            return rows
        if item.comparison_mode == "cheapest_price":
            return [row for row in rows if row["upc"] == item.preferred_upc]

        preferred_variant = self.resolve_upc(item.preferred_upc)
        preferred_brand = preferred_variant.brand if preferred_variant is not None else None
        if preferred_brand:
            normalized_brand = preferred_brand.strip().lower()
            brand_rows = [
                row for row in rows
                if row["variant_brand"] is not None and str(row["variant_brand"]).strip().lower() == normalized_brand
            ]
            if brand_rows:
                return brand_rows
        return [row for row in rows if row["upc"] == item.preferred_upc]

    def _candidate_plans_for_group(
        self,
        item: ShoppingOptimizationInput,
        requested_quantity: CanonicalQuantity,
        rows: list[sqlite3.Row],
        best_value_dimension: Optional[str] = None,
    ) -> list[CandidatePlan]:
        latest_sale: Optional[EffectivePriceSource] = None
        latest_non_sale: Optional[EffectivePriceSource] = None
        for row in rows:
            if bool(row["is_sale"]):
                if latest_sale is None and self._is_sale_active(row):
                    latest_sale = self._to_effective_price_source(row, is_sale=True)
            elif latest_non_sale is None:
                latest_non_sale = self._to_effective_price_source(row, is_sale=False)
            if latest_sale is not None and latest_non_sale is not None:
                break

        reference_row = latest_sale.row if latest_sale is not None else latest_non_sale.row if latest_non_sale is not None else None
        if reference_row is None:
            return []
        per_purchase_quantity = self._per_purchase_quantity(reference_row, item.desired_quantity_unit)
        if per_purchase_quantity is None or per_purchase_quantity.dimension != requested_quantity.dimension:
            heuristic_quantity = self._heuristic_count_request_quantity(reference_row, item)
            if heuristic_quantity is None:
                return []
            required_units = max(1, math.ceil(heuristic_quantity - 1e-9))
            return self._candidate_plans_from_required_units(
                item=item,
                latest_sale=latest_sale,
                latest_non_sale=latest_non_sale,
                per_purchase_quantity=1.0,
                required_units=required_units,
                approximation_warning=(
                    "Approximate 1:1 conversion used between requested unit and count-based variant."
                ),
                best_value_dimension=best_value_dimension,
            )
        if per_purchase_quantity.quantity <= 0:
            return []

        required_units = max(1, math.ceil(requested_quantity.quantity / per_purchase_quantity.quantity - 1e-9))
        return self._candidate_plans_from_required_units(
            item=item,
            latest_sale=latest_sale,
            latest_non_sale=latest_non_sale,
            per_purchase_quantity=per_purchase_quantity.quantity,
            required_units=required_units,
            best_value_dimension=best_value_dimension,
        )

    def _candidate_plans_from_required_units(
        self,
        item: ShoppingOptimizationInput,
        latest_sale: Optional[EffectivePriceSource],
        latest_non_sale: Optional[EffectivePriceSource],
        per_purchase_quantity: float,
        required_units: int,
        approximation_warning: Optional[str] = None,
        best_value_dimension: Optional[str] = None,
    ) -> list[CandidatePlan]:
        plans: list[CandidatePlan] = []

        if latest_non_sale is not None:
            plans.append(
                self._build_candidate_plan(
                    row=latest_non_sale.row,
                    item=item,
                    per_purchase_quantity=per_purchase_quantity,
                    sale_units=0,
                    non_sale_units=required_units,
                    sale_source=latest_sale,
                    non_sale_source=latest_non_sale,
                    approximation_warning=approximation_warning,
                    best_value_dimension=best_value_dimension,
                )
            )

        if latest_sale is None:
            return plans

        for sale_units in self._allowed_sale_units(latest_sale, required_units):
            if sale_units >= required_units:
                plans.append(
                    self._build_candidate_plan(
                        row=latest_sale.row,
                        item=item,
                        per_purchase_quantity=per_purchase_quantity,
                        sale_units=sale_units,
                        non_sale_units=0,
                        sale_source=latest_sale,
                        non_sale_source=latest_non_sale,
                        approximation_warning=approximation_warning,
                        best_value_dimension=best_value_dimension,
                    )
                )
            elif latest_non_sale is not None:
                plans.append(
                    self._build_candidate_plan(
                        row=latest_sale.row,
                        item=item,
                        per_purchase_quantity=per_purchase_quantity,
                        sale_units=sale_units,
                        non_sale_units=required_units - sale_units,
                        sale_source=latest_sale,
                        non_sale_source=latest_non_sale,
                        approximation_warning=approximation_warning,
                        best_value_dimension=best_value_dimension,
                    )
                )

        return plans

    def _heuristic_count_request_quantity(
        self,
        row: sqlite3.Row,
        item: ShoppingOptimizationInput,
    ) -> Optional[float]:
        observed_unit = ProductUnit(int(row["quantity_unit"]))
        if observed_unit != ProductUnit.EA:
            return None
        if item.desired_quantity_unit == ProductUnit.EA:
            return None
        return float(item.desired_count)

    def _candidate_sort_key(self, candidate: CandidatePlan) -> tuple[float, float, str]:
        if candidate.item.comparison_mode == "best_unit_value":
            return (
                candidate.unit_value_score,
                candidate.estimated_total_price,
                -self._observed_at_sort_value(candidate.row["observed_at"]),
            )
        return (
            candidate.estimated_total_price,
            candidate.unit_value_score,
            -self._observed_at_sort_value(candidate.row["observed_at"]),
        )

    def _observed_at_sort_value(self, observed_at: str) -> float:
        return self._coerce_utc(dt.datetime.fromisoformat(observed_at)).timestamp()

    def _select_best_single_store(self, candidates_by_item: dict[int, list[CandidatePlan]]) -> Optional[int]:
        by_store: dict[int, list[CandidatePlan]] = defaultdict(list)
        for item_candidates in candidates_by_item.values():
            seen_store_ids: set[int] = set()
            for candidate in item_candidates:
                store_id = int(candidate.row["store_id"])
                if store_id in seen_store_ids:
                    continue
                by_store[store_id].append(candidate)
                seen_store_ids.add(store_id)

        if not by_store:
            return None

        def score(store_id: int) -> tuple[int, float, int]:
            store_candidates = by_store[store_id]
            return (-len(store_candidates), sum(c.estimated_total_price for c in store_candidates), store_id)

        return min(by_store.keys(), key=score)

    def _candidate_to_match(self, candidate: CandidatePlan) -> ShoppingOptimizationMatch:
        row = candidate.row
        return ShoppingOptimizationMatch(
            item_id=candidate.item.item_id,
            comparison_mode=candidate.item.comparison_mode,
            desired_count=float(candidate.item.desired_count),
            store_id=int(row["store_id"]),
            store_name=row["store_name"],
            store_address=row["store_address"],
            store_latitude=float(row["store_latitude"]) if row["store_latitude"] is not None else None,
            store_longitude=float(row["store_longitude"]) if row["store_longitude"] is not None else None,
            store_requires_paid_membership=bool(row["store_requires_paid_membership"]),
            upc=row["upc"],
            product_name=row["product_name"],
            variant_label=row["variant_label"],
            variant_brand=row["variant_brand"],
            variant_flavor=row["variant_flavor"],
            variant_packaging_style=self._packaging_style_from_db(row["variant_packaging_style"]),
            pack_count=int(row["pack_count"]),
            net_quantity=float(row["net_quantity"]),
            quantity_unit=ProductUnit(int(row["quantity_unit"])),
            price_observation_id=int(row["price_observation_id"]),
            observed_price_total=float(row["price_total"]),
            observed_at=row["observed_at"],
            estimated_total_price=candidate.estimated_total_price,
            requires_paid_membership=candidate.requires_paid_membership,
            requires_loyalty_card=candidate.requires_loyalty_card,
            pricing_basis_line=candidate.pricing_basis_line,
            pricing_equation_line=candidate.pricing_equation_line,
            approximation_warning=candidate.approximation_warning,
        )

    def _build_candidate_plan(
        self,
        row: sqlite3.Row,
        item: ShoppingOptimizationInput,
        per_purchase_quantity: float,
        sale_units: int,
        non_sale_units: int,
        sale_source: Optional[EffectivePriceSource],
        non_sale_source: Optional[EffectivePriceSource],
        approximation_warning: Optional[str] = None,
        best_value_dimension: Optional[str] = None,
    ) -> CandidatePlan:
        sale_total = float(sale_units) * (sale_source.unit_price if sale_source is not None else 0.0)
        non_sale_total = float(non_sale_units) * (non_sale_source.unit_price if non_sale_source is not None else 0.0)
        total_observation_units = sale_units + non_sale_units
        total_supplied_quantity = per_purchase_quantity * total_observation_units
        estimated_total_price = sale_total + non_sale_total
        score_quantity = total_supplied_quantity
        if best_value_dimension is not None:
            measurable_quantity = self._package_quantity_for_dimension(row, best_value_dimension)
            if measurable_quantity is not None and measurable_quantity > 0:
                score_quantity = measurable_quantity * total_observation_units
        unit_value_score = estimated_total_price / score_quantity
        requires_paid_membership = bool(row["store_requires_paid_membership"]) or (sale_units > 0 and sale_source is not None and sale_source.requires_paid_membership)
        requires_loyalty_card = sale_units > 0 and sale_source is not None and sale_source.requires_loyalty_card
        pricing_basis_line, pricing_equation_line = self._build_pricing_display(
            row=row,
            item=item,
            per_purchase_quantity=per_purchase_quantity,
            sale_units=sale_units,
            non_sale_units=non_sale_units,
            sale_source=sale_source,
            non_sale_source=non_sale_source,
            estimated_total_price=estimated_total_price,
            total_supplied_quantity=total_supplied_quantity,
        )
        return CandidatePlan(
            row=row,
            item=item,
            estimated_total_price=estimated_total_price,
            total_supplied_quantity=total_supplied_quantity,
            unit_value_score=unit_value_score,
            total_observation_units=total_observation_units,
            sale_units=sale_units,
            non_sale_units=non_sale_units,
            requires_paid_membership=requires_paid_membership,
            requires_loyalty_card=requires_loyalty_card,
            pricing_basis_line=pricing_basis_line,
            pricing_equation_line=pricing_equation_line,
            approximation_warning=approximation_warning,
        )

    def _allowed_sale_units(self, source: EffectivePriceSource, required_units: int) -> list[int]:
        step = max(1, int(source.multiple_of) if source.multiple_of is not None else 1)
        minimum = max(1, int(source.minimum_quantity) if source.minimum_quantity is not None else 1)
        minimum = step * math.ceil(minimum / step)
        if source.limit_quantity is not None and int(source.limit_quantity) < minimum:
            return []
        smallest_satisfying = step * math.ceil(max(required_units, minimum) / step)
        max_units = int(source.limit_quantity) if source.limit_quantity is not None else smallest_satisfying
        cap = min(max_units, smallest_satisfying) if max_units >= smallest_satisfying else max_units
        if cap < minimum:
            return []
        return list(range(minimum, cap + 1, step))

    def _build_pricing_display(
        self,
        row: sqlite3.Row,
        item: ShoppingOptimizationInput,
        per_purchase_quantity: float,
        sale_units: int,
        non_sale_units: int,
        sale_source: Optional[EffectivePriceSource],
        non_sale_source: Optional[EffectivePriceSource],
        estimated_total_price: float,
        total_supplied_quantity: float,
    ) -> tuple[str, str]:
        package_label = self._package_label(row)
        package_quantity = self._package_quantity_display(row)
        package_unit_price = self._package_unit_price_display(row, source=(sale_source if sale_units > 0 and sale_source is not None else non_sale_source))
        desired_unit_label = self._unit_display(item.desired_quantity_unit)
        requested_quantity = self._format_number(item.desired_count)
        supplied_quantity = self._format_number(total_supplied_quantity)
        estimated_total_label = self._format_money(estimated_total_price)

        if sale_units > 0 and non_sale_units > 0 and sale_source is not None and non_sale_source is not None:
            basis = (
                f"{package_label} sale {self._format_money(sale_source.unit_price)} "
                f"+ regular {self._format_money(non_sale_source.unit_price)}"
            )
            equation = (
                f"{sale_units} sale + {non_sale_units} regular = {estimated_total_label} "
                f"for {supplied_quantity} {desired_unit_label} (need {requested_quantity})"
            )
            return basis, equation

        source = sale_source if sale_units > 0 and sale_source is not None else non_sale_source
        units = sale_units if sale_units > 0 else non_sale_units
        unit_price = source.unit_price if source is not None else float(row["price_total"])
        basis = f"{package_label}{package_quantity} @ {self._format_money(unit_price)}{package_unit_price}"
        equation = self._single_source_equation(
            row=row,
            units=units,
            unit_price=unit_price,
            estimated_total_label=estimated_total_label,
            supplied_quantity=supplied_quantity,
            desired_unit_label=desired_unit_label,
            requested_quantity=requested_quantity,
        )
        return basis, equation

    def _single_source_equation(
        self,
        row: sqlite3.Row,
        units: int,
        unit_price: float,
        estimated_total_label: str,
        supplied_quantity: str,
        desired_unit_label: str,
        requested_quantity: str,
    ) -> str:
        unit = ProductUnit(int(row["quantity_unit"]))
        count = max(1, int(row["pack_count"]) if row["pack_count"] is not None else 1)
        if unit != ProductUnit.EA:
            total_quantity = float(row["net_quantity"])
            if not bool(row["is_variable_weight"]):
                total_quantity *= count
            unit_price_display = self._format_money(unit_price / total_quantity)
            return (
                f"{units} x {self._format_number(total_quantity)} {self._unit_display(unit)} "
                f"* {unit_price_display}/{self._unit_display(unit)} = {estimated_total_label}"
            )
        return (
            f"{units} x {self._package_label(row).lower()} = {estimated_total_label} "
            f"for {supplied_quantity} {desired_unit_label} (need {requested_quantity})"
        )

    def _package_unit_price_display(
        self,
        row: sqlite3.Row,
        source: Optional[EffectivePriceSource],
    ) -> str:
        unit = ProductUnit(int(row["quantity_unit"]))
        if unit == ProductUnit.EA:
            return ""
        quantity = float(row["net_quantity"])
        if not bool(row["is_variable_weight"]):
            quantity *= max(1, int(row["pack_count"]) if row["pack_count"] is not None else 1)
        if quantity <= 0:
            return ""
        unit_price = (source.unit_price if source is not None else float(row["price_total"])) / quantity
        return f" = {self._format_money(unit_price)}/{self._unit_display(unit)}"

    def _package_label(self, row: sqlite3.Row) -> str:
        packaging_style = self._packaging_style_from_db(row["variant_packaging_style"])
        packaging_display = self._packaging_style_display(packaging_style)
        count = max(1, int(row["pack_count"]) if row["pack_count"] is not None else 1)
        if bool(row["is_variable_weight"]):
            return f"1 {packaging_display}"
        if count == 1:
            return f"1 {packaging_display}"
        return f"{count} {packaging_display}"

    def _package_quantity_display(self, row: sqlite3.Row) -> str:
        unit = ProductUnit(int(row["quantity_unit"]))
        quantity = float(row["net_quantity"])
        count = max(1, int(row["pack_count"]) if row["pack_count"] is not None else 1)
        if bool(row["is_variable_weight"]):
            return f" / {self._format_number(quantity)} {self._unit_display(unit)}"
        if unit == ProductUnit.EA:
            return ""
        total_quantity = quantity * count
        return f" ({self._format_number(total_quantity)} {self._unit_display(unit)})"

    def _package_quantity_for_dimension(
        self,
        row: sqlite3.Row,
        dimension: str,
    ) -> Optional[float]:
        unit = ProductUnit(int(row["quantity_unit"]))
        if unit == ProductUnit.EA:
            return None
        quantity = float(row["net_quantity"])
        if not bool(row["is_variable_weight"]):
            quantity *= max(1, int(row["pack_count"]) if row["pack_count"] is not None else 1)
        canonical = self._to_canonical_quantity(quantity, unit)
        if canonical is None or canonical.dimension != dimension:
            return None
        return canonical.quantity

    def _format_money(self, value: float) -> str:
        return f"${value:.2f}"

    def _format_number(self, value: float) -> str:
        rounded = round(value)
        if abs(value - rounded) < 1e-9:
            return str(int(rounded))
        return f"{value:.2f}".rstrip("0").rstrip(".")

    def _unit_display(self, unit: ProductUnit) -> str:
        return {
            ProductUnit.OZ: "oz",
            ProductUnit.LB: "lb",
            ProductUnit.EA: "item",
            ProductUnit.KG: "kg",
            ProductUnit.G: "g",
            ProductUnit.LIT: "L",
            ProductUnit.ML: "mL",
            ProductUnit.GAL: "gal",
            ProductUnit.QT: "qt",
            ProductUnit.PT: "pt",
            ProductUnit.TSP: "tsp",
            ProductUnit.TBSP: "tbsp",
            ProductUnit.FL_OZ: "fl oz",
            ProductUnit.CUP: "cup",
        }[unit]

    def _packaging_style_display(self, style: Optional[PackagingStyle]) -> str:
        return {
            PackagingStyle.UNSPECIFIED: "package",
            PackagingStyle.LOOSE: "loose",
            PackagingStyle.CAN: "can",
            PackagingStyle.BOTTLE: "bottle",
            PackagingStyle.BOX: "box",
            PackagingStyle.BAG: "bag",
            PackagingStyle.CARTON: "carton",
            PackagingStyle.BUNCH: "bunch",
            PackagingStyle.OTHER: "package",
            None: "package",
        }[style]

    def _to_effective_price_source(self, row: sqlite3.Row, is_sale: bool) -> EffectivePriceSource:
        return EffectivePriceSource(
            row=row,
            is_sale=is_sale,
            unit_price=float(row["price_total"]),
            minimum_quantity=row["minimum_quantity"] if is_sale else None,
            limit_quantity=row["limit_quantity"] if is_sale else None,
            multiple_of=row["multiple_of"] if is_sale else None,
            requires_paid_membership=bool(row["store_requires_paid_membership"]) or bool(row["sale_requires_paid_membership"]),
            requires_loyalty_card=bool(row["sale_requires_loyalty_card"]),
        )

    def _is_sale_active(self, row: sqlite3.Row) -> bool:
        start_date = row["start_date"]
        if start_date is None:
            return False
        now = dt.datetime.now(dt.timezone.utc)
        start = self._parse_temporal_value(start_date)
        expiration = self._parse_temporal_value(row["expiration_date"]) if row["expiration_date"] is not None else None
        if isinstance(start, dt.date) and not isinstance(start, dt.datetime):
            if start > now.date():
                return False
        elif isinstance(start, dt.datetime):
            if self._coerce_utc(start) > now:
                return False
        if expiration is None:
            return True
        if isinstance(expiration, dt.date) and not isinstance(expiration, dt.datetime):
            return expiration >= now.date()
        return self._coerce_utc(expiration) >= now

    def _coerce_utc(self, value: dt.datetime) -> dt.datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.timezone.utc)
        return value.astimezone(dt.timezone.utc)

    def _parse_temporal_value(self, value: str) -> dt.date | dt.datetime:
        if "T" not in value:
            return dt.date.fromisoformat(value)
        return dt.datetime.fromisoformat(value)

    def _per_purchase_quantity(
        self,
        row: sqlite3.Row,
        desired_quantity_unit: ProductUnit,
    ) -> Optional[CanonicalQuantity]:
        observed_unit = ProductUnit(int(row["quantity_unit"]))
        if desired_quantity_unit == ProductUnit.EA:
            if bool(row["is_variable_weight"]):
                return CanonicalQuantity(dimension="count", quantity=1.0)
            return CanonicalQuantity(
                dimension="count",
                quantity=float(max(1, int(row["pack_count"]) if row["pack_count"] is not None else 1)),
            )
        base_quantity = float(row["net_quantity"])
        if not bool(row["is_variable_weight"]):
            base_quantity *= max(1, int(row["pack_count"]) if row["pack_count"] is not None else 1)
        canonical_quantity = self._to_canonical_quantity(base_quantity, observed_unit)
        desired_canonical = self._to_canonical_quantity(1.0, desired_quantity_unit)
        if canonical_quantity is None or desired_canonical is None:
            return None
        if canonical_quantity.dimension != desired_canonical.dimension:
            return None
        return canonical_quantity

    def _unit_dimensions(self, unit: ProductUnit) -> set[str]:
        canonical_quantity = self._to_canonical_quantity(quantity=1.0, unit=unit)
        if canonical_quantity is None:
            return set()
        return {canonical_quantity.dimension}

    def _to_canonical_quantity(
        self,
        quantity: float,
        unit: ProductUnit,
    ) -> Optional[CanonicalQuantity]:
        if unit == ProductUnit.EA:
            return CanonicalQuantity(dimension="count", quantity=quantity)
        factor = self._mass_factor(unit)
        if factor is not None:
            return CanonicalQuantity(dimension="mass", quantity=quantity * factor)
        factor = self._volume_factor(unit)
        if factor is not None:
            return CanonicalQuantity(dimension="volume", quantity=quantity * factor)
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
        if unit == ProductUnit.FL_OZ:
            return 29.5735295625
        if unit == ProductUnit.CUP:
            return 236.5882365
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
        normalized_brand = self._normalize_descriptor(payload.brand)
        normalized_flavor = self._normalize_descriptor(payload.flavor)
        normalized_label = self._build_variant_label(
            brand=normalized_brand,
            flavor=normalized_flavor,
            packaging_style=payload.packaging_style,
            fallback=payload.variant_label,
        )
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
                    brand = ?,
                    flavor = ?,
                    packaging_style = ?,
                    pack_count = ?,
                    net_quantity = ?,
                    quantity_unit = ?,
                    is_variable_weight = ?,
                    updated_at = ?
                WHERE rowid = ?
                """,
                (
                    normalized_label,
                    normalized_brand,
                    normalized_flavor,
                    self._packaging_style_to_db(payload.packaging_style),
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
              AND COALESCE(brand, '') = COALESCE(?, '')
              AND COALESCE(flavor, '') = COALESCE(?, '')
              AND COALESCE(packaging_style, '') = COALESCE(?, '')
              AND pack_count = ?
              AND net_quantity = ?
              AND quantity_unit = ?
            """,
            (
                product_id,
                normalized_brand,
                normalized_flavor,
                self._packaging_style_to_db(payload.packaging_style),
                payload.pack_count,
                payload.net_quantity,
                int(payload.quantity_unit.value),
            ),
        ).fetchone()
        if natural_key_row is not None:
            connection.execute(
                """
                UPDATE variants
                SET upc = ?, label = ?, brand = ?, flavor = ?, packaging_style = ?, is_variable_weight = ?, updated_at = ?
                WHERE rowid = ?
                """,
                (
                    payload.upc,
                    normalized_label,
                    normalized_brand,
                    normalized_flavor,
                    self._packaging_style_to_db(payload.packaging_style),
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
                brand,
                flavor,
                packaging_style,
                pack_count,
                net_quantity,
                quantity_unit,
                is_variable_weight,
                upc,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                normalized_label,
                normalized_brand,
                normalized_flavor,
                self._packaging_style_to_db(payload.packaging_style),
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
            INSERT INTO sales(
                limit_quantity,
                expiration_date,
                start_date,
                minimum_quantity,
                multiple_of,
                requires_paid_membership,
                requires_loyalty_card
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sale.limit_quantity,
                sale.expiration_date,
                sale.start_date,
                sale.minimum_quantity,
                sale.multiple_of,
                int(sale.requires_paid_membership),
                int(sale.requires_loyalty_card),
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
            brand=row["brand"],
            flavor=row["flavor"],
            packaging_style=self._packaging_style_from_db(row["packaging_style"]),
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
            multiple_of=row["multiple_of"],
            requires_paid_membership=bool(row["sale_requires_paid_membership"]),
            requires_loyalty_card=bool(row["sale_requires_loyalty_card"]),
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

    def _normalize_descriptor(self, raw: Optional[str]) -> Optional[str]:
        if raw is None:
            return None
        normalized = raw.strip().lower()
        return normalized or None

    def _build_variant_label(
        self,
        brand: Optional[str],
        flavor: Optional[str],
        packaging_style: Optional[PackagingStyle],
        fallback: str,
    ) -> str:
        parts = [part for part in [brand, flavor, self._packaging_style_to_display(packaging_style)] if part]
        if parts:
            return " ".join(dict.fromkeys(parts))
        normalized_fallback = fallback.strip().lower()
        if not normalized_fallback:
            raise ValueError("Variant details are required")
        return normalized_fallback

    def _packaging_style_to_db(self, packaging_style: Optional[PackagingStyle]) -> Optional[str]:
        if packaging_style in (None, PackagingStyle.UNSPECIFIED):
            return None
        return packaging_style.name.lower()

    def _packaging_style_from_db(self, raw: Optional[str]) -> Optional[PackagingStyle]:
        if raw is None:
            return None
        normalized = raw.strip().upper()
        if not normalized:
            return None
        return PackagingStyle[normalized]

    def _packaging_style_to_display(self, packaging_style: Optional[PackagingStyle]) -> Optional[str]:
        if packaging_style in (None, PackagingStyle.UNSPECIFIED):
            return None
        return packaging_style.name.lower()

    def _utc_now_iso(self) -> str:
        return dt.datetime.now(dt.timezone.utc).isoformat(timespec="microseconds")
