from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from db_server.db.bootstrap import create_database
from db_server.domain.commands import PriceObservationInput, SaleInput
from db_server.domain.upc import ProductUnit
from db_server.repositories import GroceryRepository


class GroceryRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.repository = GroceryRepository(create_database(db_path))

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_create_and_resolve_upc(self) -> None:
        observation_id = self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                upc="123456",
                product_name="Milk",
                product_category="Dairy",
                variant_label="Whole",
                pack_count=1,
                net_quantity=64.0,
                quantity_unit=ProductUnit.OZ,
                is_variable_weight=False,
                price_total=4.99,
                observed_at="2026-03-03T10:00:00+00:00",
                is_sale=False,
            )
        )

        self.assertGreater(observation_id, 0)

        variant = self.repository.resolve_upc("123456")
        self.assertIsNotNone(variant)
        assert variant is not None
        self.assertEqual(variant.product.name, "milk")
        self.assertEqual(variant.label, "Whole")

        observation = self.repository.get_price_observation(observation_id)
        self.assertIsNotNone(observation)
        assert observation is not None
        self.assertEqual(observation.store.address, "123 Main St")
        self.assertIsNone(observation.sale)

    def test_existing_upc_updates_variant_and_reuses_records(self) -> None:
        first_id = self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                upc="123456",
                product_name="Milk",
                product_category=None,
                variant_label="Whole",
                pack_count=1,
                net_quantity=64.0,
                quantity_unit=ProductUnit.OZ,
                is_variable_weight=False,
                price_total=4.99,
                observed_at="2026-03-03T10:00:00+00:00",
                is_sale=False,
            )
        )
        second_id = self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=11.0,
                store_longitude=21.0,
                store_name=None,
                upc="123456",
                product_name="Milk",
                product_category="Dairy",
                variant_label="Whole Updated",
                pack_count=2,
                net_quantity=128.0,
                quantity_unit=ProductUnit.OZ,
                is_variable_weight=True,
                price_total=5.99,
                observed_at="2026-03-03T11:00:00+00:00",
                is_sale=False,
            )
        )

        self.assertNotEqual(first_id, second_id)
        variant = self.repository.resolve_upc("123456")
        self.assertIsNotNone(variant)
        assert variant is not None
        self.assertEqual(variant.label, "Whole Updated")
        self.assertEqual(variant.pack_count, 2)
        self.assertTrue(variant.is_variable_weight)

    def test_sale_is_persisted(self) -> None:
        observation_id = self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                upc="654321",
                product_name="Eggs",
                product_category="Dairy",
                variant_label="12 count",
                pack_count=1,
                net_quantity=12.0,
                quantity_unit=ProductUnit.EA,
                is_variable_weight=False,
                price_total=2.99,
                observed_at="2026-03-03T10:00:00+00:00",
                is_sale=True,
                sale=SaleInput(
                    start_date="2026-03-01T00:00:00+00:00",
                    expiration_date="2026-03-05T00:00:00+00:00",
                    minimum_quantity=1,
                    limit_quantity=2,
                ),
            )
        )

        observation = self.repository.get_price_observation(observation_id)
        self.assertIsNotNone(observation)
        assert observation is not None
        self.assertIsNotNone(observation.sale)
        assert observation.sale is not None
        self.assertEqual(observation.sale.limit_quantity, 2)

    def test_categories_are_normalized(self) -> None:
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                upc="222222",
                product_name="Cola",
                product_category=" Drinks ; Soda;Drinks ; Caffeine ",
                variant_label="12 pack",
                pack_count=12,
                net_quantity=12.0,
                quantity_unit=ProductUnit.OZ,
                is_variable_weight=False,
                price_total=8.99,
                observed_at="2026-03-03T10:00:00+00:00",
                is_sale=False,
            )
        )

        variant = self.repository.resolve_upc("222222")
        self.assertIsNotNone(variant)
        assert variant is not None
        self.assertEqual(variant.product.category, "drinks; soda; caffeine")

    def test_conflicting_upc_raises(self) -> None:
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                upc="999999",
                product_name="Milk",
                product_category=None,
                variant_label="Whole",
                pack_count=1,
                net_quantity=64.0,
                quantity_unit=ProductUnit.OZ,
                is_variable_weight=False,
                price_total=4.99,
                observed_at="2026-03-03T10:00:00+00:00",
                is_sale=False,
            )
        )

        with self.assertRaises(ValueError):
            self.repository.create_price_observation(
                PriceObservationInput(
                    store_address="999 Elm St",
                    store_latitude=30.0,
                    store_longitude=40.0,
                    store_name="Other",
                    upc="999999",
                    product_name="Bread",
                    product_category=None,
                    variant_label="White",
                    pack_count=1,
                    net_quantity=16.0,
                    quantity_unit=ProductUnit.OZ,
                    is_variable_weight=False,
                    price_total=3.49,
                    observed_at="2026-03-03T12:00:00+00:00",
                    is_sale=False,
                )
            )

    def test_list_products_returns_sorted_catalog(self) -> None:
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                upc="777777",
                product_name="Bananas",
                product_category="Produce",
                variant_label="bunch",
                pack_count=1,
                net_quantity=1.0,
                quantity_unit=ProductUnit.EA,
                is_variable_weight=False,
                price_total=1.99,
                observed_at="2026-03-03T10:00:00+00:00",
                is_sale=False,
            )
        )
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                upc="888888",
                product_name="Apples",
                product_category="Produce",
                variant_label="bag",
                pack_count=1,
                net_quantity=3.0,
                quantity_unit=ProductUnit.LB,
                is_variable_weight=False,
                price_total=4.99,
                observed_at="2026-03-03T10:00:00+00:00",
                is_sale=False,
            )
        )

        products = self.repository.list_products()

        self.assertEqual(["apples", "bananas"], [product.name for product in products])

    def test_list_variants_for_product_returns_matching_variants(self) -> None:
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                upc="313131",
                product_name="chips",
                product_category="snacks",
                variant_label="barbecue",
                pack_count=1,
                net_quantity=8.0,
                quantity_unit=ProductUnit.OZ,
                is_variable_weight=False,
                price_total=3.49,
                observed_at="2026-03-03T10:00:00+00:00",
                is_sale=False,
            )
        )

        variants = self.repository.list_variants_for_product("CHIPS")

        self.assertEqual(1, len(variants))
        self.assertEqual("barbecue", variants[0].label)

    def test_list_products_can_return_incremental_updates(self) -> None:
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                upc="111100",
                product_name="cereal",
                product_category="breakfast",
                variant_label="family size",
                pack_count=1,
                net_quantity=18.0,
                quantity_unit=ProductUnit.OZ,
                is_variable_weight=False,
                price_total=5.99,
                observed_at="2026-03-03T10:00:00+00:00",
                is_sale=False,
            )
        )
        sync_token = self.repository.get_catalog_sync_token()
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                upc="111101",
                product_name="coffee",
                product_category="drinks",
                variant_label="ground",
                pack_count=1,
                net_quantity=12.0,
                quantity_unit=ProductUnit.OZ,
                is_variable_weight=False,
                price_total=7.99,
                observed_at="2026-03-03T10:01:00+00:00",
                is_sale=False,
            )
        )

        products = self.repository.list_products(updated_after=sync_token)

        self.assertEqual(["coffee"], [product.name for product in products])

    def test_list_variants_for_product_can_return_incremental_updates(self) -> None:
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                upc="414141",
                product_name="tea",
                product_category="drinks",
                variant_label="green",
                pack_count=1,
                net_quantity=20.0,
                quantity_unit=ProductUnit.EA,
                is_variable_weight=False,
                price_total=4.49,
                observed_at="2026-03-03T10:00:00+00:00",
                is_sale=False,
            )
        )
        sync_token = self.repository.get_variant_sync_token("tea")
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                upc="414142",
                product_name="tea",
                product_category="drinks",
                variant_label="black",
                pack_count=1,
                net_quantity=20.0,
                quantity_unit=ProductUnit.EA,
                is_variable_weight=False,
                price_total=4.99,
                observed_at="2026-03-03T10:01:00+00:00",
                is_sale=False,
            )
        )

        variants = self.repository.list_variants_for_product("tea", updated_after=sync_token)

        self.assertEqual(["black"], [variant.label for variant in variants])
