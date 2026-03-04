from __future__ import annotations

from concurrent import futures
from pathlib import Path
from typing import Optional

import grpc

from db_server import db_service_pb2
from db_server import db_service_pb2_grpc
from db_server.db.bootstrap import create_database
from db_server.domain.commands import PriceObservationInput, SaleInput
from db_server.domain.upc import ProductUnit, ProductVariant
from db_server.repositories import GroceryRepository


class GroceryServicer(
    db_service_pb2_grpc.UpcServiceServicer,
    db_service_pb2_grpc.CatalogServiceServicer,
    db_service_pb2_grpc.ObservationServiceServicer,
):
    def __init__(self, repository: GroceryRepository):
        self.repository = repository

    def ResolveUpc(
        self,
        request: db_service_pb2.UpcRequest,
        context: grpc.ServicerContext,
    ) -> db_service_pb2.UpcResponse:
        upc = request.upc.strip()
        if len(upc) < 4 or not upc.isdigit():
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "UPC must be at least 4 digits")

        variant = self.repository.resolve_upc(upc)
        response = db_service_pb2.UpcResponse(found=variant is not None)
        if variant is not None:
            response.info.CopyFrom(self._to_upc_info(variant))
        return response

    def ListProducts(
        self,
        request: db_service_pb2.ListProductsRequest,
        context: grpc.ServicerContext,
    ) -> db_service_pb2.ListProductsResponse:
        updated_after = request.updatedAfter if request.HasField("updatedAfter") else None
        response = db_service_pb2.ListProductsResponse(
            nextSyncToken=self.repository.get_catalog_sync_token(),
        )
        for product in self.repository.list_products(updated_after):
            entry = response.products.add(
                productId=product.rowid,
                productName=product.name,
                updatedAt=product.updated_at,
            )
            if product.category is not None:
                entry.productCategory = product.category
        return response

    def ListVariantsForProduct(
        self,
        request: db_service_pb2.ListVariantsForProductRequest,
        context: grpc.ServicerContext,
    ) -> db_service_pb2.ListVariantsForProductResponse:
        product_name = request.productName.strip()
        if not product_name:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "productName is required")

        updated_after = request.updatedAfter if request.HasField("updatedAfter") else None
        response = db_service_pb2.ListVariantsForProductResponse(
            nextSyncToken=self.repository.get_variant_sync_token(product_name),
        )
        for variant in self.repository.list_variants_for_product(product_name, updated_after):
            response.variants.add().CopyFrom(self._to_upc_info(variant))
        return response

    def CreatePriceObservation(
        self,
        request: db_service_pb2.PriceObservationRequest,
        context: grpc.ServicerContext,
    ) -> db_service_pb2.PriceObservationResponse:
        try:
            payload = self._to_price_observation_input(request)
            observation_id = self.repository.create_price_observation(payload)
        except ValueError as exc:
            if str(exc) == "UPC already exists for a different product":
                context.abort(grpc.StatusCode.ALREADY_EXISTS, str(exc))
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        return db_service_pb2.PriceObservationResponse(observationId=observation_id)

    def _to_upc_info(self, variant: ProductVariant) -> db_service_pb2.UpcInfo:
        info = db_service_pb2.UpcInfo(
            upc=variant.upc,
            productName=variant.product.name,
            variantLabel=variant.label,
            packCount=variant.pack_count,
            netQuantity=variant.net_quantity,
            quantityUnit=variant.quantity_unit.value,
            isVariableWeight=variant.is_variable_weight,
            updatedAt=variant.updated_at,
        )
        if variant.product.category is not None:
            info.productCategory = variant.product.category
        return info

    def _to_price_observation_input(
        self,
        request: db_service_pb2.PriceObservationRequest,
    ) -> PriceObservationInput:
        self._validate_request(request)

        sale = None
        if request.HasField("saleInfo"):
            sale = SaleInput(
                start_date=request.saleInfo.startDate,
                expiration_date=(
                    request.saleInfo.expirationDate
                    if request.saleInfo.HasField("expirationDate")
                    else None
                ),
                minimum_quantity=(
                    request.saleInfo.minimumQuantity
                    if request.saleInfo.HasField("minimumQuantity")
                    else None
                ),
                limit_quantity=(
                    request.saleInfo.limitQuantity
                    if request.saleInfo.HasField("limitQuantity")
                    else None
                ),
            )

        return PriceObservationInput(
            store_address=request.store.storeAddress.strip(),
            store_latitude=request.store.location.latitude,
            store_longitude=request.store.location.longitude,
            store_name=request.store.storeName.strip() if request.store.HasField("storeName") else None,
            upc=request.upc.upc.strip(),
            product_name=request.upc.productName.strip(),
            product_category=(
                request.upc.productCategory.strip()
                if request.upc.HasField("productCategory")
                else None
            ),
            variant_label=request.upc.variantLabel.strip(),
            pack_count=request.upc.packCount,
            net_quantity=request.upc.netQuantity,
            quantity_unit=ProductUnit(request.upc.quantityUnit),
            is_variable_weight=request.upc.isVariableWeight,
            price_total=request.priceTotal,
            observed_at=request.observedAt.strip(),
            is_sale=request.isSale,
            sale=sale,
        )

    def _validate_request(self, request: db_service_pb2.PriceObservationRequest) -> None:
        if not request.store.storeAddress.strip():
            raise ValueError("Store address is required")
        if not request.upc.upc.strip().isdigit() or len(request.upc.upc.strip()) < 4:
            raise ValueError("UPC must contain only digits and be at least 4 digits")
        if not request.upc.productName.strip():
            raise ValueError("Product name is required")
        if not request.upc.variantLabel.strip():
            raise ValueError("Variant label is required")
        if request.upc.packCount <= 0:
            raise ValueError("Pack count must be greater than zero")
        if request.upc.netQuantity <= 0:
            raise ValueError("Net quantity must be greater than zero")
        if request.priceTotal < 0:
            raise ValueError("Price must be non-negative")
        if not request.observedAt.strip():
            raise ValueError("observedAt is required")
        if request.isSale and not request.HasField("saleInfo"):
            raise ValueError("saleInfo is required when isSale is true")
        if request.HasField("saleInfo") and not request.saleInfo.startDate.strip():
            raise ValueError("saleInfo.startDate is required")


def create_servicer(db_path: Path) -> GroceryServicer:
    database = create_database(db_path)
    return GroceryServicer(GroceryRepository(database))


def serve(host: str, port: int, db_path: Path) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = create_servicer(db_path)
    db_service_pb2_grpc.add_UpcServiceServicer_to_server(servicer, server)
    db_service_pb2_grpc.add_CatalogServiceServicer_to_server(servicer, server)
    db_service_pb2_grpc.add_ObservationServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    print(f"Listening on {host}:{port}")
    return server
