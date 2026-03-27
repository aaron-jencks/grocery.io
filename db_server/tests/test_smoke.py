from __future__ import annotations

import tempfile
import unittest
from concurrent import futures
from pathlib import Path

import grpc

from db_server import db_service_pb2
from db_server import db_service_pb2_grpc
from db_server.domain.upc import ProductUnit
from db_server.parsing import ParsedPriceTag
from db_server.server import create_servicer


class SmokeTestPriceTagParser:
    def parse(self, image_jpeg: bytes, image_filename: str | None = None) -> ParsedPriceTag:
        _ = image_jpeg
        _ = image_filename
        return ParsedPriceTag(
            ambiguous=False,
            unparsable=False,
            upc_parsable=False,
            upc=None,
            price_total=3.99,
            pack_count=1,
            net_quantity=10.0,
            quantity_unit=ProductUnit.OZ,
            is_variable_weight=False,
            message="ok",
        )


class GroceryGrpcSmokeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        self.db_path = root / "smoke.sqlite3"
        self.training_dir = root / "training"

        servicer = create_servicer(
            self.db_path,
            training_data_dir=self.training_dir,
            price_tag_parser=SmokeTestPriceTagParser(),
        )
        self.server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        db_service_pb2_grpc.add_UpcServiceServicer_to_server(servicer, self.server)
        db_service_pb2_grpc.add_CatalogServiceServicer_to_server(servicer, self.server)
        db_service_pb2_grpc.add_StoreServiceServicer_to_server(servicer, self.server)
        db_service_pb2_grpc.add_ObservationServiceServicer_to_server(servicer, self.server)
        db_service_pb2_grpc.add_ParsingServiceServicer_to_server(servicer, self.server)
        db_service_pb2_grpc.add_ShoppingServiceServicer_to_server(servicer, self.server)
        try:
            port = self.server.add_insecure_port("0.0.0.0:0")
        except RuntimeError as exc:
            self.skipTest(f"gRPC port binding unavailable in this environment: {exc}")
        if port <= 0:
            self.skipTest("gRPC port binding unavailable in this environment")
        self.server.start()

        self.channel = grpc.insecure_channel(f"127.0.0.1:{port}")
        grpc.channel_ready_future(self.channel).result(timeout=5)
        self.upc_stub = db_service_pb2_grpc.UpcServiceStub(self.channel)
        self.catalog_stub = db_service_pb2_grpc.CatalogServiceStub(self.channel)
        self.store_stub = db_service_pb2_grpc.StoreServiceStub(self.channel)
        self.observation_stub = db_service_pb2_grpc.ObservationServiceStub(self.channel)
        self.parsing_stub = db_service_pb2_grpc.ParsingServiceStub(self.channel)
        self.shopping_stub = db_service_pb2_grpc.ShoppingServiceStub(self.channel)

    def tearDown(self) -> None:
        self.channel.close()
        self.server.stop(grace=None)
        self.temp_dir.cleanup()

    def test_end_to_end_local_smoke(self) -> None:
        parse_response = self.parsing_stub.ParsePriceTagImage(
            db_service_pb2.ParsePriceTagImageRequest(
                imageJpeg=b"fake-jpeg-bytes",
                imageFilename="smoke.jpg",
            ),
            timeout=5,
        )
        self.assertFalse(parse_response.ambiguous)
        self.assertFalse(parse_response.unparsable)
        self.assertEqual(3.99, parse_response.priceTotal)
        self.assertEqual(db_service_pb2.OZ, parse_response.quantityUnit)

        create_response = self.observation_stub.CreatePriceObservation(
            db_service_pb2.PriceObservationRequest(
                store=db_service_pb2.StoreInfo(
                    storeAddress="123 Main St",
                    location=db_service_pb2.Coordinate(latitude=1.0, longitude=2.0),
                    storeName="Smoke Store",
                ),
                upc=db_service_pb2.UpcInfo(
                    upc="123456",
                    productName="Green Grapes",
                    productCategory="Fruit",
                    variantLabel="White Tiger Seedless Bag",
                    brand="White Tiger",
                    flavor="Seedless",
                    packagingStyle=db_service_pb2.BAG,
                    packCount=1,
                    netQuantity=1.0,
                    quantityUnit=db_service_pb2.LB,
                    isVariableWeight=True,
                ),
                priceTotal=3.99,
                observedAt="2026-03-13T12:00:00+00:00",
                isSale=False,
                trainingImageJpeg=b"fake-jpeg-bytes",
                trainingImageFilename="smoke.jpg",
                trainingImageUpcPresent=False,
            ),
            timeout=5,
        )
        self.assertGreater(create_response.observationId, 0)

        store_response = self.store_stub.FindStoreByAddress(
            db_service_pb2.StoreLookupRequest(storeAddress="123 Main St"),
            timeout=5,
        )
        self.assertTrue(store_response.found)
        self.assertEqual("Smoke Store", store_response.store.storeName)

        resolve_response = self.upc_stub.ResolveUpc(
            db_service_pb2.UpcRequest(upc="123456"),
            timeout=5,
        )
        self.assertTrue(resolve_response.found)
        self.assertEqual("green grapes", resolve_response.info.productName)

        products_response = self.catalog_stub.ListProducts(
            db_service_pb2.ListProductsRequest(),
            timeout=5,
        )
        self.assertEqual(1, len(products_response.products))
        self.assertEqual("green grapes", products_response.products[0].productName)

        variants_response = self.catalog_stub.ListVariantsForProduct(
            db_service_pb2.ListVariantsForProductRequest(productName="green grapes"),
            timeout=5,
        )
        self.assertEqual(1, len(variants_response.variants))
        self.assertEqual("123456", variants_response.variants[0].upc)

        optimize_response = self.shopping_stub.OptimizeGroceryList(
                db_service_pb2.OptimizeGroceryListRequest(
                    items=[
                        db_service_pb2.GroceryListOptimizationItem(
                            itemId=1,
                            productName="green grapes",
                            desiredCount=1,
                            comparisonMode=db_service_pb2.CHEAPEST_PRICE,
                        preferredUpc="123456",
                    )
                ]
            ),
            timeout=5,
        )
        self.assertEqual(1, len(optimize_response.matches))
        self.assertEqual("Smoke Store", optimize_response.matches[0].store.storeName)
