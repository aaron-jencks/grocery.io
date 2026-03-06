from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

import grpc

from db_server import db_service_pb2
from db_server.domain.upc import ProductUnit
from db_server.parsing import ParsedPriceTag
from db_server.server import create_servicer


class FakeContext:
    def abort(self, code: grpc.StatusCode, details: str):
        raise RpcAbort(code, details)


class RpcAbort(Exception):
    def __init__(self, code: grpc.StatusCode, details: str):
        super().__init__(details)
        self.code = code
        self.details = details


class GroceryServicerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.training_dir = Path(self.temp_dir.name) / "training_data"
        self.fake_parsed_result = ParsedPriceTag(
            ambiguous=False,
            unparsable=False,
            upc_parsable=True,
            upc="123456789012",
            price_total=5.49,
            pack_count=2,
            net_quantity=12.0,
            quantity_unit=ProductUnit.OZ,
            is_variable_weight=False,
            message="ok",
        )
        self.fake_parser = FakePriceTagParser(lambda *_: self.fake_parsed_result)
        self.servicer = create_servicer(
            Path(self.temp_dir.name) / "test.sqlite3",
            training_data_dir=self.training_dir,
            price_tag_parser=self.fake_parser,
        )
        self.context = FakeContext()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_resolve_upc_round_trip(self) -> None:
        create_response = self.servicer.CreatePriceObservation(
            db_service_pb2.PriceObservationRequest(
                store=db_service_pb2.StoreInfo(
                    storeAddress="123 Main St",
                    location=db_service_pb2.Coordinate(latitude=1.0, longitude=2.0),
                    storeName="Store",
                ),
                upc=db_service_pb2.UpcInfo(
                    upc="123456",
                    productName="Milk",
                    productCategory="Dairy",
                    variantLabel="Whole",
                    packCount=1,
                    netQuantity=64.0,
                    quantityUnit=db_service_pb2.OZ,
                    isVariableWeight=False,
                ),
                priceTotal=4.99,
                observedAt="2026-03-03T10:00:00+00:00",
                isSale=False,
            ),
            self.context,
        )

        self.assertTrue(create_response.HasField("observationId"))

        response = self.servicer.ResolveUpc(
            db_service_pb2.UpcRequest(upc="123456"),
            self.context,
        )
        self.assertTrue(response.found)
        self.assertEqual(response.info.productName, "milk")

    def test_invalid_upc_is_rejected(self) -> None:
        with self.assertRaises(RpcAbort) as raised:
            self.servicer.ResolveUpc(
                db_service_pb2.UpcRequest(upc="abc"),
                self.context,
            )

        self.assertEqual(raised.exception.code, grpc.StatusCode.INVALID_ARGUMENT)

    def test_sale_requires_sale_info(self) -> None:
        with self.assertRaises(RpcAbort) as raised:
            self.servicer.CreatePriceObservation(
                db_service_pb2.PriceObservationRequest(
                    store=db_service_pb2.StoreInfo(
                        storeAddress="123 Main St",
                        location=db_service_pb2.Coordinate(latitude=1.0, longitude=2.0),
                    ),
                    upc=db_service_pb2.UpcInfo(
                        upc="123456",
                        productName="Milk",
                        variantLabel="Whole",
                        packCount=1,
                        netQuantity=64.0,
                        quantityUnit=db_service_pb2.OZ,
                        isVariableWeight=False,
                    ),
                    priceTotal=4.99,
                    observedAt="2026-03-03T10:00:00+00:00",
                    isSale=True,
                ),
                self.context,
            )

        self.assertEqual(raised.exception.code, grpc.StatusCode.INVALID_ARGUMENT)

    def test_list_products_returns_catalog(self) -> None:
        self.servicer.CreatePriceObservation(
            db_service_pb2.PriceObservationRequest(
                store=db_service_pb2.StoreInfo(
                    storeAddress="123 Main St",
                    location=db_service_pb2.Coordinate(latitude=1.0, longitude=2.0),
                ),
                upc=db_service_pb2.UpcInfo(
                    upc="999123",
                    productName="Yogurt",
                    productCategory="Dairy",
                    variantLabel="Vanilla",
                    packCount=1,
                    netQuantity=6.0,
                    quantityUnit=db_service_pb2.OZ,
                    isVariableWeight=False,
                ),
                priceTotal=1.99,
                observedAt="2026-03-03T10:00:00+00:00",
                isSale=False,
            ),
            self.context,
        )

        response = self.servicer.ListProducts(
            db_service_pb2.ListProductsRequest(),
            self.context,
        )

        self.assertEqual(1, len(response.products))
        self.assertEqual("yogurt", response.products[0].productName)

    def test_list_products_respects_updated_after(self) -> None:
        self.servicer.CreatePriceObservation(
            db_service_pb2.PriceObservationRequest(
                store=db_service_pb2.StoreInfo(
                    storeAddress="123 Main St",
                    location=db_service_pb2.Coordinate(latitude=1.0, longitude=2.0),
                ),
                upc=db_service_pb2.UpcInfo(
                    upc="900001",
                    productName="cereal",
                    variantLabel="family size",
                    packCount=1,
                    netQuantity=18.0,
                    quantityUnit=db_service_pb2.OZ,
                    isVariableWeight=False,
                ),
                priceTotal=5.99,
                observedAt="2026-03-03T10:00:00+00:00",
                isSale=False,
            ),
            self.context,
        )
        first_response = self.servicer.ListProducts(
            db_service_pb2.ListProductsRequest(),
            self.context,
        )
        self.servicer.CreatePriceObservation(
            db_service_pb2.PriceObservationRequest(
                store=db_service_pb2.StoreInfo(
                    storeAddress="123 Main St",
                    location=db_service_pb2.Coordinate(latitude=1.0, longitude=2.0),
                ),
                upc=db_service_pb2.UpcInfo(
                    upc="900002",
                    productName="granola",
                    variantLabel="box",
                    packCount=1,
                    netQuantity=12.0,
                    quantityUnit=db_service_pb2.OZ,
                    isVariableWeight=False,
                ),
                priceTotal=4.99,
                observedAt="2026-03-03T10:01:00+00:00",
                isSale=False,
            ),
            self.context,
        )

        response = self.servicer.ListProducts(
            db_service_pb2.ListProductsRequest(updatedAfter=first_response.nextSyncToken),
            self.context,
        )

        self.assertEqual(1, len(response.products))
        self.assertEqual("granola", response.products[0].productName)

    def test_list_variants_for_product_returns_variants(self) -> None:
        self.servicer.CreatePriceObservation(
            db_service_pb2.PriceObservationRequest(
                store=db_service_pb2.StoreInfo(
                    storeAddress="123 Main St",
                    location=db_service_pb2.Coordinate(latitude=1.0, longitude=2.0),
                ),
                upc=db_service_pb2.UpcInfo(
                    upc="222333",
                    productName="chips",
                    productCategory="snacks",
                    variantLabel="salted",
                    packCount=1,
                    netQuantity=8.0,
                    quantityUnit=db_service_pb2.OZ,
                    isVariableWeight=False,
                ),
                priceTotal=2.99,
                observedAt="2026-03-03T10:00:00+00:00",
                isSale=False,
            ),
            self.context,
        )

        response = self.servicer.ListVariantsForProduct(
            db_service_pb2.ListVariantsForProductRequest(productName="Chips"),
            self.context,
        )

        self.assertEqual(1, len(response.variants))
        self.assertEqual("salted", response.variants[0].variantLabel)

    def test_conflicting_upc_returns_already_exists(self) -> None:
        self.servicer.CreatePriceObservation(
            db_service_pb2.PriceObservationRequest(
                store=db_service_pb2.StoreInfo(
                    storeAddress="123 Main St",
                    location=db_service_pb2.Coordinate(latitude=1.0, longitude=2.0),
                ),
                upc=db_service_pb2.UpcInfo(
                    upc="555444",
                    productName="milk",
                    variantLabel="whole",
                    packCount=1,
                    netQuantity=64.0,
                    quantityUnit=db_service_pb2.OZ,
                    isVariableWeight=False,
                ),
                priceTotal=4.99,
                observedAt="2026-03-03T10:00:00+00:00",
                isSale=False,
            ),
            self.context,
        )

        with self.assertRaises(RpcAbort) as raised:
            self.servicer.CreatePriceObservation(
                db_service_pb2.PriceObservationRequest(
                    store=db_service_pb2.StoreInfo(
                        storeAddress="123 Main St",
                        location=db_service_pb2.Coordinate(latitude=1.0, longitude=2.0),
                    ),
                    upc=db_service_pb2.UpcInfo(
                        upc="555444",
                        productName="bread",
                        variantLabel="white",
                        packCount=1,
                        netQuantity=16.0,
                        quantityUnit=db_service_pb2.OZ,
                        isVariableWeight=False,
                    ),
                    priceTotal=2.99,
                    observedAt="2026-03-03T10:01:00+00:00",
                    isSale=False,
                ),
                self.context,
            )

        self.assertEqual(grpc.StatusCode.ALREADY_EXISTS, raised.exception.code)

    def test_optimize_grocery_list_returns_match_and_unmatched(self) -> None:
        self.servicer.CreatePriceObservation(
            db_service_pb2.PriceObservationRequest(
                store=db_service_pb2.StoreInfo(
                    storeAddress="123 Main St",
                    location=db_service_pb2.Coordinate(latitude=1.0, longitude=2.0),
                    storeName="Store A",
                ),
                upc=db_service_pb2.UpcInfo(
                    upc="101010",
                    productName="milk",
                    variantLabel="half gallon",
                    packCount=1,
                    netQuantity=0.5,
                    quantityUnit=db_service_pb2.GAL,
                    isVariableWeight=False,
                ),
                priceTotal=2.5,
                observedAt="2026-03-03T10:00:00+00:00",
                isSale=False,
            ),
            self.context,
        )

        response = self.servicer.OptimizeGroceryList(
            db_service_pb2.OptimizeGroceryListRequest(
                items=[
                    db_service_pb2.GroceryListOptimizationItem(
                        itemId=1,
                        productName="milk",
                        desiredCount=1,
                        comparisonMode=db_service_pb2.BEST_UNIT_VALUE,
                    ),
                    db_service_pb2.GroceryListOptimizationItem(
                        itemId=2,
                        productName="unknown product",
                        desiredCount=1,
                        comparisonMode=db_service_pb2.CHEAPEST_PRICE,
                    ),
                ]
            ),
            self.context,
        )

        self.assertEqual(1, len(response.matches))
        self.assertEqual(1, len(response.unmatched))
        self.assertEqual(1, response.matches[0].itemId)
        self.assertEqual("101010", response.matches[0].variant.upc)
        self.assertEqual(
            db_service_pb2.BEST_UNIT_VALUE,
            response.matches[0].comparisonMode,
        )
        self.assertEqual(2, response.unmatched[0].itemId)

    def test_optimize_grocery_list_rejects_blank_product_name(self) -> None:
        with self.assertRaises(RpcAbort) as raised:
            self.servicer.OptimizeGroceryList(
                db_service_pb2.OptimizeGroceryListRequest(
                    items=[
                        db_service_pb2.GroceryListOptimizationItem(
                            itemId=1,
                            productName="   ",
                            desiredCount=1,
                            comparisonMode=db_service_pb2.CHEAPEST_PRICE,
                        )
                    ]
                ),
                self.context,
            )

        self.assertEqual(grpc.StatusCode.INVALID_ARGUMENT, raised.exception.code)

    def test_create_price_observation_with_training_image_persists_dataset_artifacts(self) -> None:
        response = self.servicer.CreatePriceObservation(
            db_service_pb2.PriceObservationRequest(
                store=db_service_pb2.StoreInfo(
                    storeAddress="123 Main St",
                    location=db_service_pb2.Coordinate(latitude=1.0, longitude=2.0),
                    storeName="Store A",
                ),
                upc=db_service_pb2.UpcInfo(
                    upc="909090",
                    productName="milk",
                    variantLabel="whole",
                    packCount=1,
                    netQuantity=64.0,
                    quantityUnit=db_service_pb2.OZ,
                    isVariableWeight=False,
                ),
                priceTotal=4.99,
                observedAt="2026-03-03T10:00:00+00:00",
                isSale=False,
                trainingImageJpeg=b"fake-jpeg-bytes",
                trainingImageFilename="capture.jpg",
            ),
            self.context,
        )

        self.assertTrue(response.HasField("observationId"))
        labels_path = self.training_dir / "labels.json"
        images_dir = self.training_dir / "images"
        self.assertTrue(labels_path.exists())
        self.assertTrue(images_dir.exists())
        payload = json.loads(labels_path.read_text())
        self.assertEqual(1, len(payload))
        self.assertEqual("labeled", payload[0]["status"])
        self.assertEqual("909090", payload[0]["upc_code"])
        image_filename = payload[0]["image_filename"]
        self.assertTrue((images_dir / image_filename).exists())

    def test_parse_price_tag_image_returns_parsed_fields(self) -> None:
        response = self.servicer.ParsePriceTagImage(
            db_service_pb2.ParsePriceTagImageRequest(
                imageJpeg=b"fake-bytes",
                imageFilename="capture.jpg",
            ),
            self.context,
        )

        self.assertFalse(response.ambiguous)
        self.assertFalse(response.unparsable)
        self.assertTrue(response.upcParsable)
        self.assertTrue(response.HasField("upc"))
        self.assertEqual("123456789012", response.upc)
        self.assertEqual(2, response.packCount)
        self.assertEqual(db_service_pb2.OZ, response.quantityUnit)
        self.assertEqual("capture.jpg", self.fake_parser.last_filename)

    def test_parse_price_tag_image_requires_payload(self) -> None:
        with self.assertRaises(RpcAbort) as raised:
            self.servicer.ParsePriceTagImage(
                db_service_pb2.ParsePriceTagImageRequest(),
                self.context,
            )

        self.assertEqual(grpc.StatusCode.INVALID_ARGUMENT, raised.exception.code)


class FakePriceTagParser:
    def __init__(self, fn):
        self._fn = fn
        self.last_filename: str | None = None

    def parse(self, image_jpeg: bytes, image_filename: str | None = None) -> ParsedPriceTag:
        _ = image_jpeg
        self.last_filename = image_filename
        return self._fn(image_jpeg, image_filename)
