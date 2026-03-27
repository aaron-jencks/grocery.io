from __future__ import annotations

import argparse
import tempfile
from concurrent import futures
from pathlib import Path

import grpc

from db_server import db_service_pb2
from db_server import db_service_pb2_grpc
from db_server.domain.upc import ProductUnit
from db_server.parsing import ParsedPriceTag, PriceTagParser, create_default_price_tag_parser
from db_server.server import create_servicer


class SmokeTestPriceTagParser(PriceTagParser):
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--disable-ai", action="store_true")
    parser.add_argument("--image", default="")
    parser.add_argument("--timeout-seconds", type=float, default=30.0)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        db_path = root / "smoke.sqlite3"
        training_dir = root / "training"
        parse_image_bytes = b"fake-jpeg-bytes"
        parse_image_name = "smoke.jpg"
        price_tag_parser: PriceTagParser | None = SmokeTestPriceTagParser()
        if not args.disable_ai:
            image_path = Path(args.image) if args.image else _find_default_smoke_image()
            parse_image_bytes = image_path.read_bytes()
            parse_image_name = image_path.name
            price_tag_parser = create_default_price_tag_parser()

        servicer = create_servicer(
            db_path,
            training_data_dir=training_dir,
            price_tag_parser=price_tag_parser,
        )
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=4))
        db_service_pb2_grpc.add_UpcServiceServicer_to_server(servicer, server)
        db_service_pb2_grpc.add_CatalogServiceServicer_to_server(servicer, server)
        db_service_pb2_grpc.add_StoreServiceServicer_to_server(servicer, server)
        db_service_pb2_grpc.add_ObservationServiceServicer_to_server(servicer, server)
        db_service_pb2_grpc.add_ParsingServiceServicer_to_server(servicer, server)
        db_service_pb2_grpc.add_ShoppingServiceServicer_to_server(servicer, server)
        port = server.add_insecure_port(f"{args.host}:0")
        if port <= 0:
            raise RuntimeError(f"Failed to bind local gRPC smoke server on {args.host}:0")
        server.start()

        try:
            channel = grpc.insecure_channel(f"{args.host}:{port}")
            grpc.channel_ready_future(channel).result(timeout=5)
            upc_stub = db_service_pb2_grpc.UpcServiceStub(channel)
            catalog_stub = db_service_pb2_grpc.CatalogServiceStub(channel)
            store_stub = db_service_pb2_grpc.StoreServiceStub(channel)
            observation_stub = db_service_pb2_grpc.ObservationServiceStub(channel)
            parsing_stub = db_service_pb2_grpc.ParsingServiceStub(channel)
            shopping_stub = db_service_pb2_grpc.ShoppingServiceStub(channel)

            parse_response = parsing_stub.ParsePriceTagImage(
                db_service_pb2.ParsePriceTagImageRequest(
                    imageJpeg=parse_image_bytes,
                    imageFilename=parse_image_name,
                ),
                timeout=args.timeout_seconds,
            )
            if not args.disable_ai:
                print(
                    "AI parse response:",
                    {
                        "ambiguous": parse_response.ambiguous,
                        "unparsable": parse_response.unparsable,
                        "upcParsable": parse_response.upcParsable,
                        "priceTotal": parse_response.priceTotal if parse_response.HasField("priceTotal") else None,
                        "packCount": parse_response.packCount if parse_response.HasField("packCount") else None,
                        "netQuantity": parse_response.netQuantity if parse_response.HasField("netQuantity") else None,
                        "quantityUnit": parse_response.quantityUnit if parse_response.HasField("quantityUnit") else None,
                        "isVariableWeight": parse_response.isVariableWeight,
                        "message": parse_response.message if parse_response.HasField("message") else None,
                    },
                )
            else:
                assert not parse_response.ambiguous
                assert not parse_response.unparsable

            create_response = observation_stub.CreatePriceObservation(
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
                    trainingImageJpeg=parse_image_bytes,
                    trainingImageFilename=parse_image_name,
                    trainingImageUpcPresent=False,
                ),
                timeout=args.timeout_seconds,
            )
            assert create_response.observationId > 0

            store_response = store_stub.FindStoreByAddress(
                db_service_pb2.StoreLookupRequest(storeAddress="123 Main St"),
                timeout=args.timeout_seconds,
            )
            assert store_response.found
            assert store_response.store.storeName == "Smoke Store"

            resolve_response = upc_stub.ResolveUpc(
                db_service_pb2.UpcRequest(upc="123456"),
                timeout=args.timeout_seconds,
            )
            assert resolve_response.found

            products_response = catalog_stub.ListProducts(
                db_service_pb2.ListProductsRequest(),
                timeout=args.timeout_seconds,
            )
            assert len(products_response.products) == 1

            variants_response = catalog_stub.ListVariantsForProduct(
                db_service_pb2.ListVariantsForProductRequest(productName="green grapes"),
                timeout=args.timeout_seconds,
            )
            assert len(variants_response.variants) == 1

            optimize_response = shopping_stub.OptimizeGroceryList(
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
                timeout=args.timeout_seconds,
            )
            assert len(optimize_response.matches) == 1
            print("Smoke test passed.")
        finally:
            channel.close()
            server.stop(grace=None)


def _find_default_smoke_image() -> Path:
    image_dir = Path(__file__).resolve().parent.parent / "ai_server" / "data" / "images"
    candidates = sorted(image_dir.glob("*.jpg"))
    if not candidates:
        raise FileNotFoundError(f"No JPG images found under {image_dir}")
    return candidates[0]


if __name__ == "__main__":
    main()
