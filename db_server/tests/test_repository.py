from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from db_server.db.bootstrap import create_database
from db_server.domain.commands import PriceObservationInput, SaleInput
from db_server.domain.upc import ProductUnit
from db_server.repositories import GroceryRepository
from db_server.repositories.grocery import ShoppingOptimizationInput


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
        self.assertEqual(variant.label, "whole")

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
        self.assertEqual(variant.label, "whole updated")
        self.assertEqual(variant.pack_count, 2)
        self.assertTrue(variant.is_variable_weight)


    def test_sale_is_persisted(self) -> None:
        observation_id = self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store",
                store_requires_paid_membership=True,
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
                    multiple_of=3,
                    requires_paid_membership=True,
                    requires_loyalty_card=True,
                ),
            )
        )

        observation = self.repository.get_price_observation(observation_id)
        self.assertIsNotNone(observation)
        assert observation is not None
        self.assertIsNotNone(observation.sale)
        assert observation.sale is not None
        self.assertEqual(observation.sale.limit_quantity, 2)
        self.assertEqual(observation.sale.multiple_of, 3)
        self.assertTrue(observation.store.requires_paid_membership)
        self.assertTrue(observation.sale.requires_paid_membership)
        self.assertTrue(observation.sale.requires_loyalty_card)

    def test_optimize_filters_paid_membership_and_loyalty_rows(self) -> None:
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="123 Main St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Members Store",
                store_requires_paid_membership=True,
                upc="666001",
                product_name="milk",
                product_category=None,
                variant_label="gallon",
                pack_count=1,
                net_quantity=1.0,
                quantity_unit=ProductUnit.GAL,
                is_variable_weight=False,
                price_total=3.00,
                observed_at="2026-03-03T10:00:00+00:00",
                is_sale=True,
                sale=SaleInput(
                    start_date="2026-03-01T00:00:00+00:00",
                    requires_paid_membership=True,
                    requires_loyalty_card=True,
                ),
            )
        )
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="500 Oak St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Open Store",
                upc="666002",
                product_name="milk",
                product_category=None,
                variant_label="gallon",
                pack_count=1,
                net_quantity=1.0,
                quantity_unit=ProductUnit.GAL,
                is_variable_weight=False,
                price_total=4.00,
                observed_at="2026-03-03T10:01:00+00:00",
                is_sale=False,
            )
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="milk",
                    desired_count=1,
                    desired_quantity_unit=ProductUnit.GAL,
                    comparison_mode="cheapest_price",
                    preferred_upc=None,
                    allow_paid_membership_required=False,
                    allow_loyalty_card_required=False,
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual(1, len(matches))
        self.assertEqual("666002", matches[0].upc)
        self.assertFalse(matches[0].requires_paid_membership)
        self.assertFalse(matches[0].requires_loyalty_card)

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

    def test_optimize_cheapest_price_uses_per_item_cost(self) -> None:
        self._create_observation(
            upc="700001",
            product_name="soda",
            variant_label="single can",
            pack_count=1,
            net_quantity=12.0,
            quantity_unit=ProductUnit.OZ,
            price_total=2.00,
            observed_at="2026-03-03T10:00:00+00:00",
            store_address="123 Main St",
            store_name="Store A",
        )
        self._create_observation(
            upc="700002",
            product_name="soda",
            variant_label="12-pack",
            pack_count=12,
            net_quantity=12.0,
            quantity_unit=ProductUnit.OZ,
            price_total=15.00,
            observed_at="2026-03-03T10:01:00+00:00",
            store_address="500 Oak St",
            store_name="Store B",
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="soda",
                    desired_count=288,
                    desired_quantity_unit=ProductUnit.OZ,
                    comparison_mode="cheapest_price",
                    preferred_upc=None,
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual(1, len(matches))
        self.assertEqual("700002", matches[0].upc)
        self.assertAlmostEqual(30.0, matches[0].estimated_total_price, places=6)

    def test_optimize_best_unit_value_converts_volume_units(self) -> None:
        self._create_observation(
            upc="710001",
            product_name="milk",
            variant_label="half gallon",
            pack_count=1,
            net_quantity=0.5,
            quantity_unit=ProductUnit.GAL,
            price_total=2.60,
            observed_at="2026-03-03T10:00:00+00:00",
            store_address="111 First Ave",
            store_name="Store A",
        )
        self._create_observation(
            upc="710002",
            product_name="milk",
            variant_label="1 liter",
            pack_count=1,
            net_quantity=1.0,
            quantity_unit=ProductUnit.LIT,
            price_total=1.60,
            observed_at="2026-03-03T10:02:00+00:00",
            store_address="222 Second Ave",
            store_name="Store B",
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="milk",
                    desired_count=1000,
                    desired_quantity_unit=ProductUnit.ML,
                    comparison_mode="best_unit_value",
                    preferred_upc=None,
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual("710001", matches[0].upc)

    def test_optimize_best_unit_value_converts_fl_oz_volume_units(self) -> None:
        self._create_observation(
            upc="710101",
            product_name="juice",
            variant_label="12 fl oz can",
            pack_count=1,
            net_quantity=12.0,
            quantity_unit=ProductUnit.FL_OZ,
            price_total=1.00,
            observed_at="2026-03-03T10:00:00+00:00",
            store_address="111 First Ave",
            store_name="Store A",
        )
        self._create_observation(
            upc="710102",
            product_name="juice",
            variant_label="500 ml bottle",
            pack_count=1,
            net_quantity=500.0,
            quantity_unit=ProductUnit.ML,
            price_total=1.60,
            observed_at="2026-03-03T10:01:00+00:00",
            store_address="222 Second Ave",
            store_name="Store B",
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="juice",
                    desired_count=500,
                    desired_quantity_unit=ProductUnit.ML,
                    comparison_mode="best_unit_value",
                    preferred_upc=None,
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual("710101", matches[0].upc)

    def test_optimize_best_unit_value_converts_cup_volume_units(self) -> None:
        self._create_observation(
            upc="710201",
            product_name="stock",
            variant_label="2 cups carton",
            pack_count=1,
            net_quantity=2.0,
            quantity_unit=ProductUnit.CUP,
            price_total=1.80,
            observed_at="2026-03-03T10:00:00+00:00",
            store_address="111 First Ave",
            store_name="Store A",
        )
        self._create_observation(
            upc="710202",
            product_name="stock",
            variant_label="500 ml carton",
            pack_count=1,
            net_quantity=500.0,
            quantity_unit=ProductUnit.ML,
            price_total=1.20,
            observed_at="2026-03-03T10:01:00+00:00",
            store_address="222 Second Ave",
            store_name="Store B",
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="stock",
                    desired_count=500,
                    desired_quantity_unit=ProductUnit.ML,
                    comparison_mode="best_unit_value",
                    preferred_upc=None,
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual("710202", matches[0].upc)

    def test_optimize_best_unit_value_converts_mass_units(self) -> None:
        self._create_observation(
            upc="720001",
            product_name="rice",
            variant_label="1 lb",
            pack_count=1,
            net_quantity=1.0,
            quantity_unit=ProductUnit.LB,
            price_total=2.20,
            observed_at="2026-03-03T10:00:00+00:00",
            store_address="333 Third Ave",
            store_name="Store A",
        )
        self._create_observation(
            upc="720002",
            product_name="rice",
            variant_label="1 kg",
            pack_count=1,
            net_quantity=1.0,
            quantity_unit=ProductUnit.KG,
            price_total=4.00,
            observed_at="2026-03-03T10:01:00+00:00",
            store_address="444 Fourth Ave",
            store_name="Store B",
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="rice",
                    desired_count=1000,
                    desired_quantity_unit=ProductUnit.G,
                    comparison_mode="best_unit_value",
                    preferred_upc=None,
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual("720002", matches[0].upc)

    def test_optimize_best_unit_value_item_request_prefers_larger_measurable_package(self) -> None:
        self._create_observation(
            upc="720101",
            product_name="granulated sugar",
            variant_label="giant eagle bag",
            pack_count=1,
            net_quantity=4.0,
            quantity_unit=ProductUnit.LB,
            price_total=3.99,
            observed_at="2026-03-26T17:49:42-04:00",
            store_address="2801 N High St, Columbus, OH 43202, USA",
            store_name="giant eagle",
        )
        self._create_observation(
            upc="720102",
            product_name="granulated sugar",
            variant_label="giant eagle bag",
            pack_count=1,
            net_quantity=10.0,
            quantity_unit=ProductUnit.LB,
            price_total=8.29,
            observed_at="2026-03-26T17:52:04-04:00",
            store_address="2801 N High St, Columbus, OH 43202, USA",
            store_name="giant eagle",
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="granulated sugar",
                    desired_count=1,
                    desired_quantity_unit=ProductUnit.EA,
                    comparison_mode="best_unit_value",
                    preferred_upc=None,
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual("720102", matches[0].upc)
        self.assertIn("$0.83/lb", matches[0].pricing_basis_line)
        self.assertIn("10 lb", matches[0].pricing_equation_line)

    def test_optimize_best_unit_value_uses_package_count_for_item_requests(self) -> None:
        self._create_observation(
            upc="730001",
            product_name="soap",
            variant_label="3 count",
            pack_count=1,
            net_quantity=3.0,
            quantity_unit=ProductUnit.EA,
            price_total=5.00,
            observed_at="2026-03-03T10:00:00+00:00",
            store_address="555 Fifth Ave",
            store_name="Store A",
        )
        self._create_observation(
            upc="730002",
            product_name="soap",
            variant_label="20 oz",
            pack_count=1,
            net_quantity=20.0,
            quantity_unit=ProductUnit.OZ,
            price_total=4.00,
            observed_at="2026-03-03T10:01:00+00:00",
            store_address="666 Sixth Ave",
            store_name="Store B",
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="soap",
                    desired_count=1,
                    desired_quantity_unit=ProductUnit.EA,
                    comparison_mode="best_unit_value",
                    preferred_upc=None,
                )
            ]
        )

        self.assertEqual(1, len(matches))
        self.assertEqual(0, len(unmatched))
        self.assertEqual("730002", matches[0].upc)

    def test_optimize_best_unit_value_preferred_upc_filters_candidates(self) -> None:
        self._create_observation(
            upc="740001",
            product_name="juice",
            variant_label="1 liter",
            pack_count=1,
            net_quantity=1.0,
            quantity_unit=ProductUnit.LIT,
            price_total=2.50,
            observed_at="2026-03-03T10:00:00+00:00",
            store_address="777 Seventh Ave",
            store_name="Store A",
        )
        self._create_observation(
            upc="740001",
            product_name="juice",
            variant_label="1 liter",
            pack_count=1,
            net_quantity=1.0,
            quantity_unit=ProductUnit.LIT,
            price_total=2.20,
            observed_at="2026-03-03T10:01:00+00:00",
            store_address="888 Eighth Ave",
            store_name="Store B",
        )
        self._create_observation(
            upc="740002",
            product_name="juice",
            variant_label="1 gallon",
            pack_count=1,
            net_quantity=1.0,
            quantity_unit=ProductUnit.GAL,
            price_total=5.00,
            observed_at="2026-03-03T10:02:00+00:00",
            store_address="999 Ninth Ave",
            store_name="Store C",
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="juice",
                    desired_count=1000,
                    desired_quantity_unit=ProductUnit.ML,
                    comparison_mode="best_unit_value",
                    preferred_upc="740001",
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual("740001", matches[0].upc)
        self.assertEqual("Store B", matches[0].store_name)

    def test_optimize_cheapest_price_prefers_exact_variant_for_item_request(self) -> None:
        self._create_observation(
            upc="740101",
            product_name="milk",
            variant_label="fairlife 2% reduced fat bottle",
            pack_count=1,
            net_quantity=52.0,
            quantity_unit=ProductUnit.FL_OZ,
            price_total=4.67,
            observed_at="2026-03-24T21:20:48-04:00",
            store_address="2801 N High St, Columbus, OH 43202, USA",
            store_name="giant eagle",
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="milk",
                    desired_count=1,
                    desired_quantity_unit=ProductUnit.EA,
                    comparison_mode="cheapest_price",
                    preferred_upc="740101",
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual(1, len(matches))
        self.assertEqual("740101", matches[0].upc)
        self.assertAlmostEqual(4.67, matches[0].estimated_total_price, places=6)

    def test_optimize_cheapest_price_heuristically_bridges_non_count_request_to_count_variant(self) -> None:
        self._create_observation(
            upc="740201",
            product_name="cilantro",
            variant_label="valverde bunch",
            pack_count=1,
            net_quantity=1.0,
            quantity_unit=ProductUnit.EA,
            price_total=0.99,
            observed_at="2026-03-10T18:38:58-04:00",
            store_address="2768 N High St, Columbus, OH 43201, USA",
            store_name="lucky's clintonville",
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="cilantro",
                    desired_count=0.25,
                    desired_quantity_unit=ProductUnit.OZ,
                    comparison_mode="cheapest_price",
                    preferred_upc="740201",
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual(1, len(matches))
        self.assertEqual("740201", matches[0].upc)
        self.assertAlmostEqual(0.99, matches[0].estimated_total_price, places=6)

    def test_optimize_cheapest_price_uses_latest_active_sale(self) -> None:
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="100 Sale St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store A",
                upc="760001",
                product_name="strawberries",
                product_category=None,
                variant_label="1 lb clamshell",
                pack_count=1,
                net_quantity=16.0,
                quantity_unit=ProductUnit.OZ,
                is_variable_weight=False,
                price_total=3.99,
                observed_at="2026-03-01T10:00:00+00:00",
                is_sale=True,
                sale=SaleInput(
                    start_date="2026-03-01T00:00:00+00:00",
                    expiration_date="2026-03-31T23:59:59+00:00",
                ),
            )
        )
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="100 Sale St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store A",
                upc="760001",
                product_name="strawberries",
                product_category=None,
                variant_label="1 lb clamshell",
                pack_count=1,
                net_quantity=16.0,
                quantity_unit=ProductUnit.OZ,
                is_variable_weight=False,
                price_total=2.99,
                observed_at="2026-03-10T10:00:00+00:00",
                is_sale=True,
                sale=SaleInput(
                    start_date="2026-03-10T00:00:00+00:00",
                    expiration_date="2026-03-31T23:59:59+00:00",
                ),
            )
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="strawberries",
                    desired_count=16,
                    desired_quantity_unit=ProductUnit.OZ,
                    comparison_mode="cheapest_price",
                    preferred_upc=None,
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual(1, len(matches))
        self.assertAlmostEqual(2.99, matches[0].estimated_total_price, places=6)
        self.assertEqual(2.99, matches[0].observed_price_total)

    def test_optimize_cheapest_price_ignores_expired_sale(self) -> None:
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="100 Sale St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store A",
                upc="760101",
                product_name="blueberries",
                product_category=None,
                variant_label="6 oz clamshell",
                pack_count=1,
                net_quantity=6.0,
                quantity_unit=ProductUnit.OZ,
                is_variable_weight=False,
                price_total=1.50,
                observed_at="2026-03-01T10:00:00+00:00",
                is_sale=True,
                sale=SaleInput(
                    start_date="2026-03-01T00:00:00+00:00",
                    expiration_date="2026-03-02T00:00:00+00:00",
                ),
            )
        )
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="100 Sale St",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store A",
                upc="760101",
                product_name="blueberries",
                product_category=None,
                variant_label="6 oz clamshell",
                pack_count=1,
                net_quantity=6.0,
                quantity_unit=ProductUnit.OZ,
                is_variable_weight=False,
                price_total=2.50,
                observed_at="2026-03-05T10:00:00+00:00",
                is_sale=False,
            )
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="blueberries",
                    desired_count=6,
                    desired_quantity_unit=ProductUnit.OZ,
                    comparison_mode="cheapest_price",
                    preferred_upc=None,
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual(1, len(matches))
        self.assertAlmostEqual(2.50, matches[0].estimated_total_price, places=6)
        self.assertEqual(2.50, matches[0].observed_price_total)

    def test_optimize_cheapest_price_uses_sale_multiple_and_non_sale_fallback(self) -> None:
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="200 Promo Ave",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store A",
                upc="760201",
                product_name="milk",
                product_category=None,
                variant_label="gallon",
                pack_count=1,
                net_quantity=1.0,
                quantity_unit=ProductUnit.GAL,
                is_variable_weight=False,
                price_total=14.0 / 3.0,
                observed_at="2026-03-20T10:00:00+00:00",
                is_sale=True,
                sale=SaleInput(
                    start_date="2026-03-20T00:00:00+00:00",
                    expiration_date="2026-03-31T23:59:59+00:00",
                    minimum_quantity=3,
                    multiple_of=3,
                    limit_quantity=3,
                ),
            )
        )
        self.repository.create_price_observation(
            PriceObservationInput(
                store_address="200 Promo Ave",
                store_latitude=10.0,
                store_longitude=20.0,
                store_name="Store A",
                upc="760201",
                product_name="milk",
                product_category=None,
                variant_label="gallon",
                pack_count=1,
                net_quantity=1.0,
                quantity_unit=ProductUnit.GAL,
                is_variable_weight=False,
                price_total=5.50,
                observed_at="2026-03-21T10:00:00+00:00",
                is_sale=False,
            )
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="milk",
                    desired_count=4,
                    desired_quantity_unit=ProductUnit.GAL,
                    comparison_mode="cheapest_price",
                    preferred_upc=None,
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual(1, len(matches))
        self.assertAlmostEqual((14.0 / 3.0) * 3 + 5.50, matches[0].estimated_total_price, places=6)

    def test_optimize_single_store_only_prefers_store_covering_most_items(self) -> None:
        self._create_observation(
            upc="760301",
            product_name="bread",
            variant_label="loaf",
            pack_count=1,
            net_quantity=16.0,
            quantity_unit=ProductUnit.OZ,
            price_total=3.00,
            observed_at="2026-03-03T10:00:00+00:00",
            store_address="10 Alpha Rd",
            store_name="Store A",
        )
        self._create_observation(
            upc="760302",
            product_name="milk",
            variant_label="gallon",
            pack_count=1,
            net_quantity=1.0,
            quantity_unit=ProductUnit.GAL,
            price_total=4.00,
            observed_at="2026-03-03T10:01:00+00:00",
            store_address="10 Alpha Rd",
            store_name="Store A",
        )
        self._create_observation(
            upc="760303",
            product_name="bread",
            variant_label="loaf",
            pack_count=1,
            net_quantity=16.0,
            quantity_unit=ProductUnit.OZ,
            price_total=2.00,
            observed_at="2026-03-03T10:02:00+00:00",
            store_address="20 Beta Rd",
            store_name="Store B",
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="bread",
                    desired_count=16,
                    desired_quantity_unit=ProductUnit.OZ,
                    comparison_mode="cheapest_price",
                    preferred_upc=None,
                    single_store_only=True,
                ),
                ShoppingOptimizationInput(
                    item_id=2,
                    product_name="milk",
                    desired_count=1,
                    desired_quantity_unit=ProductUnit.GAL,
                    comparison_mode="cheapest_price",
                    preferred_upc=None,
                    single_store_only=True,
                ),
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual(2, len(matches))
        self.assertEqual({"Store A"}, {match.store_name for match in matches})

    def test_optimize_tiebreak_prefers_newer_observation(self) -> None:
        self._create_observation(
            upc="750001",
            product_name="bread",
            variant_label="loaf",
            pack_count=1,
            net_quantity=16.0,
            quantity_unit=ProductUnit.OZ,
            price_total=3.00,
            observed_at="2026-03-03T10:00:00+00:00",
            store_address="10 Old Rd",
            store_name="Store Old",
        )
        self._create_observation(
            upc="750001",
            product_name="bread",
            variant_label="loaf",
            pack_count=1,
            net_quantity=16.0,
            quantity_unit=ProductUnit.OZ,
            price_total=3.00,
            observed_at="2026-03-03T11:00:00+00:00",
            store_address="11 New Rd",
            store_name="Store New",
        )

        matches, unmatched = self.repository.optimize_grocery_list(
            [
                ShoppingOptimizationInput(
                    item_id=1,
                    product_name="bread",
                    desired_count=16,
                    desired_quantity_unit=ProductUnit.OZ,
                    comparison_mode="cheapest_price",
                    preferred_upc="750001",
                )
            ]
        )

        self.assertEqual(0, len(unmatched))
        self.assertEqual("Store New", matches[0].store_name)

    def _create_observation(
        self,
        *,
        upc: str,
        product_name: str,
        variant_label: str,
        pack_count: int,
        net_quantity: float,
        quantity_unit: ProductUnit,
        price_total: float,
        observed_at: str,
        store_address: str,
        store_name: str,
    ) -> int:
        return self.repository.create_price_observation(
            PriceObservationInput(
                store_address=store_address,
                store_latitude=10.0,
                store_longitude=20.0,
                store_name=store_name,
                upc=upc,
                product_name=product_name,
                product_category=None,
                variant_label=variant_label,
                pack_count=pack_count,
                net_quantity=net_quantity,
                quantity_unit=quantity_unit,
                is_variable_weight=False,
                price_total=price_total,
                observed_at=observed_at,
                is_sale=False,
            )
        )
