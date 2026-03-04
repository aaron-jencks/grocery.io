from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import grpc

from db_server import db_service_pb2
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
        self.servicer = create_servicer(Path(self.temp_dir.name) / "test.sqlite3")
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
