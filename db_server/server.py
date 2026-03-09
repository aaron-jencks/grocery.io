from __future__ import annotations

import datetime as dt
import hashlib
import json
from concurrent import futures
from pathlib import Path
from typing import Optional
from uuid import uuid4

import grpc

from db_server import db_service_pb2
from db_server import db_service_pb2_grpc
from db_server.db.bootstrap import create_database
from db_server.domain.commands import PriceObservationInput, SaleInput
from db_server.domain.upc import PackagingStyle, ProductUnit, ProductVariant
from db_server.parsing import ParsedPriceTag, PriceTagParser, create_default_price_tag_parser
from db_server.repositories import GroceryRepository
from db_server.repositories.grocery import ShoppingOptimizationInput


class GroceryServicer(
    db_service_pb2_grpc.UpcServiceServicer,
    db_service_pb2_grpc.CatalogServiceServicer,
    db_service_pb2_grpc.ObservationServiceServicer,
    db_service_pb2_grpc.ParsingServiceServicer,
    db_service_pb2_grpc.ShoppingServiceServicer,
):
    def __init__(
        self,
        repository: GroceryRepository,
        training_data_dir: Optional[Path] = None,
        price_tag_parser: Optional[PriceTagParser] = None,
    ):
        self.repository = repository
        self.training_data_dir = training_data_dir
        self.price_tag_parser = price_tag_parser or create_default_price_tag_parser()
        if self.training_data_dir is not None:
            self.training_data_dir.mkdir(parents=True, exist_ok=True)
            (self.training_data_dir / "images").mkdir(parents=True, exist_ok=True)

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
            if request.HasField("trainingImageJpeg"):
                self._persist_training_sample(request, observation_id)
        except ValueError as exc:
            if str(exc) == "UPC already exists for a different product":
                context.abort(grpc.StatusCode.ALREADY_EXISTS, str(exc))
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        except Exception as exc:
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to persist training sample: {exc}")
        return db_service_pb2.PriceObservationResponse(observationId=observation_id)

    def ParsePriceTagImage(
        self,
        request: db_service_pb2.ParsePriceTagImageRequest,
        context: grpc.ServicerContext,
    ) -> db_service_pb2.ParsePriceTagImageResponse:
        if not request.imageJpeg:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "imageJpeg is required")

        filename = request.imageFilename if request.HasField("imageFilename") else None
        try:
            parsed = self.price_tag_parser.parse(
                image_jpeg=request.imageJpeg,
                image_filename=filename,
            )
        except ValueError as exc:
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(exc))
        except Exception as exc:
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to parse price-tag image: {exc}")

        return self._to_parse_response(parsed)

    def OptimizeGroceryList(
        self,
        request: db_service_pb2.OptimizeGroceryListRequest,
        context: grpc.ServicerContext,
    ) -> db_service_pb2.OptimizeGroceryListResponse:
        items: list[ShoppingOptimizationInput] = []
        for item in request.items:
            product_name = item.productName.strip()
            if not product_name:
                context.abort(grpc.StatusCode.INVALID_ARGUMENT, "productName is required")
            desired_count = max(1, int(item.desiredCount))
            mode = self._to_repo_comparison_mode(item.comparisonMode)
            preferred_upc = item.preferredUpc.strip() if item.HasField("preferredUpc") else None
            items.append(
                ShoppingOptimizationInput(
                    item_id=int(item.itemId),
                    product_name=product_name,
                    desired_count=desired_count,
                    comparison_mode=mode,
                    preferred_upc=preferred_upc or None,
                )
            )

        matches, unmatched = self.repository.optimize_grocery_list(items)

        response = db_service_pb2.OptimizeGroceryListResponse()
        for match in matches:
            entry = response.matches.add(
                itemId=match.item_id,
                comparisonMode=self._to_proto_comparison_mode(match.comparison_mode),
                desiredCount=match.desired_count,
                priceObservationId=match.price_observation_id,
                observedPriceTotal=match.observed_price_total,
                observedAt=match.observed_at,
                estimatedTotalPrice=match.estimated_total_price,
            )
            entry.store.storeId = match.store_id
            entry.store.storeAddress = match.store_address
            entry.store.location.latitude = match.store_latitude
            entry.store.location.longitude = match.store_longitude
            if match.store_name is not None:
                entry.store.storeName = match.store_name
            entry.variant.upc = match.upc
            entry.variant.productName = match.product_name
            entry.variant.variantLabel = match.variant_label
            if match.variant_brand is not None:
                entry.variant.brand = match.variant_brand
            if match.variant_flavor is not None:
                entry.variant.flavor = match.variant_flavor
            if match.variant_packaging_style is not None:
                entry.variant.packagingStyle = self._to_proto_packaging_style(match.variant_packaging_style)
            entry.variant.packCount = match.pack_count
            entry.variant.netQuantity = match.net_quantity
            entry.variant.quantityUnit = int(match.quantity_unit.value)
        for item in unmatched:
            response.unmatched.add(
                itemId=item.item_id,
                productName=item.product_name,
                reason=item.reason,
            )
        return response

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
        if variant.brand is not None:
            info.brand = variant.brand
        if variant.flavor is not None:
            info.flavor = variant.flavor
        if variant.packaging_style is not None:
            info.packagingStyle = self._to_proto_packaging_style(variant.packaging_style)
        return info

    def _to_price_observation_input(
        self,
        request: db_service_pb2.PriceObservationRequest,
    ) -> PriceObservationInput:
        self._validate_request(request)
        raw_upc = request.upc.upc.strip()
        normalized_upc = raw_upc
        if not raw_upc and request.upc.isVariableWeight:
            normalized_upc = self._derive_synthetic_variable_weight_upc(
                product_name=request.upc.productName.strip(),
                variant_label=request.upc.variantLabel.strip(),
                pack_count=request.upc.packCount,
                net_quantity=request.upc.netQuantity,
                quantity_unit=ProductUnit(request.upc.quantityUnit),
            )

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
            upc=normalized_upc,
            product_name=request.upc.productName.strip(),
            product_category=(
                request.upc.productCategory.strip()
                if request.upc.HasField("productCategory")
                else None
            ),
            variant_label=request.upc.variantLabel.strip(),
            brand=request.upc.brand.strip() if request.upc.HasField("brand") else None,
            flavor=request.upc.flavor.strip() if request.upc.HasField("flavor") else None,
            packaging_style=(
                self._from_proto_packaging_style(request.upc.packagingStyle)
                if request.upc.HasField("packagingStyle")
                else None
            ),
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
        upc = request.upc.upc.strip()
        if upc:
            if not upc.isdigit() or len(upc) < 4:
                raise ValueError("UPC must contain only digits and be at least 4 digits")
        elif not request.upc.isVariableWeight:
            raise ValueError("UPC must contain only digits and be at least 4 digits")
        if not request.upc.productName.strip():
            raise ValueError("Product name is required")
        has_variant_details = (
            request.upc.variantLabel.strip()
            or (request.upc.HasField("brand") and request.upc.brand.strip())
            or (request.upc.HasField("flavor") and request.upc.flavor.strip())
            or request.upc.HasField("packagingStyle")
        )
        if not has_variant_details:
            raise ValueError("Variant details are required")
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

    def _to_repo_comparison_mode(self, mode: int) -> str:
        if mode == db_service_pb2.BEST_UNIT_VALUE:
            return "best_unit_value"
        return "cheapest_price"

    def _to_proto_comparison_mode(self, mode: str) -> int:
        if mode == "best_unit_value":
            return db_service_pb2.BEST_UNIT_VALUE
        return db_service_pb2.CHEAPEST_PRICE

    def _derive_synthetic_variable_weight_upc(
        self,
        product_name: str,
        variant_label: str,
        pack_count: int,
        net_quantity: float,
        quantity_unit: ProductUnit,
    ) -> str:
        payload = "|".join(
            [
                product_name.lower(),
                variant_label.lower(),
                str(pack_count),
                f"{net_quantity:.6f}",
                quantity_unit.name,
                "varwt",
            ]
        )
        digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()
        numeric = int(digest[:12], 16) % 10_000_000_000
        return f"99{numeric:010d}"

    def _to_proto_packaging_style(self, value: PackagingStyle) -> int:
        mapping = {
            PackagingStyle.LOOSE: db_service_pb2.LOOSE,
            PackagingStyle.CAN: db_service_pb2.CAN,
            PackagingStyle.BOTTLE: db_service_pb2.BOTTLE,
            PackagingStyle.BOX: db_service_pb2.BOX,
            PackagingStyle.BAG: db_service_pb2.BAG,
            PackagingStyle.CARTON: db_service_pb2.CARTON,
            PackagingStyle.BUNCH: db_service_pb2.BUNCH,
            PackagingStyle.OTHER: db_service_pb2.OTHER,
        }
        return mapping.get(value, db_service_pb2.PACKAGING_UNSPECIFIED)

    def _from_proto_packaging_style(self, value: int) -> Optional[PackagingStyle]:
        mapping = {
            db_service_pb2.LOOSE: PackagingStyle.LOOSE,
            db_service_pb2.CAN: PackagingStyle.CAN,
            db_service_pb2.BOTTLE: PackagingStyle.BOTTLE,
            db_service_pb2.BOX: PackagingStyle.BOX,
            db_service_pb2.BAG: PackagingStyle.BAG,
            db_service_pb2.CARTON: PackagingStyle.CARTON,
            db_service_pb2.BUNCH: PackagingStyle.BUNCH,
            db_service_pb2.OTHER: PackagingStyle.OTHER,
        }
        return mapping.get(value)

    def _to_parse_response(self, parsed: ParsedPriceTag) -> db_service_pb2.ParsePriceTagImageResponse:
        response = db_service_pb2.ParsePriceTagImageResponse(
            ambiguous=parsed.ambiguous,
            unparsable=parsed.unparsable,
            upcParsable=parsed.upc_parsable,
            isVariableWeight=parsed.is_variable_weight,
        )
        if parsed.upc is not None:
            response.upc = parsed.upc
        if parsed.price_total is not None:
            response.priceTotal = parsed.price_total
        if parsed.pack_count is not None:
            response.packCount = parsed.pack_count
        if parsed.net_quantity is not None:
            response.netQuantity = parsed.net_quantity
        if parsed.quantity_unit is not None:
            response.quantityUnit = int(parsed.quantity_unit.value)
        if parsed.message:
            response.message = parsed.message
        return response

    def _persist_training_sample(
        self,
        request: db_service_pb2.PriceObservationRequest,
        observation_id: int,
    ) -> None:
        if self.training_data_dir is None:
            return
        image_bytes = request.trainingImageJpeg
        if not image_bytes:
            return

        labels_path = self.training_data_dir / "labels.json"
        images_dir = self.training_data_dir / "images"

        incoming_name = (
            request.trainingImageFilename.strip()
            if request.HasField("trainingImageFilename")
            else ""
        )
        extension = Path(incoming_name).suffix.lower() if incoming_name else ".jpg"
        if extension not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            extension = ".jpg"
        timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        generated_name = f"obs_{observation_id}_{timestamp}_{uuid4().hex[:8]}{extension}"
        image_path = images_dir / generated_name
        image_path.write_bytes(image_bytes)

        if labels_path.exists():
            payload = json.loads(labels_path.read_text())
            if not isinstance(payload, list):
                payload = []
        else:
            payload = []

        unit_name = db_service_pb2.ProductUnit.Name(request.upc.quantityUnit)
        if unit_name == "EA":
            unit_name = "ITEM"
        provided_upc = request.upc.upc.strip()
        upc_present = (
            bool(request.trainingImageUpcPresent)
            if request.HasField("trainingImageUpcPresent")
            else bool(provided_upc)
        )

        label_record = {
            "image_filename": generated_name,
            "status": "labeled",
            "is_ambiguous": False,
            "is_unparsable": False,
            "is_variable_weight": bool(request.upc.isVariableWeight),
            "price": float(request.priceTotal),
            "net_quantity": float(request.upc.netQuantity),
            "quantity_unit": unit_name,
            "pack_count": None if request.upc.isVariableWeight else int(request.upc.packCount),
            "upc_present": upc_present,
            "upc_code": provided_upc if upc_present else None,
            "prefilled_by_model": False,
        }
        payload.append(label_record)
        labels_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def default_training_data_dir() -> Path:
    project_root = Path(__file__).resolve().parent.parent
    return project_root / "ai_server" / "data"


def create_servicer(
    db_path: Path,
    training_data_dir: Optional[Path] = None,
    price_tag_parser: Optional[PriceTagParser] = None,
) -> GroceryServicer:
    database = create_database(db_path)
    return GroceryServicer(
        GroceryRepository(database),
        training_data_dir=training_data_dir,
        price_tag_parser=price_tag_parser,
    )


def serve(host: str, port: int, db_path: Path) -> grpc.Server:
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    servicer = create_servicer(db_path, training_data_dir=default_training_data_dir())
    db_service_pb2_grpc.add_UpcServiceServicer_to_server(servicer, server)
    db_service_pb2_grpc.add_CatalogServiceServicer_to_server(servicer, server)
    db_service_pb2_grpc.add_ObservationServiceServicer_to_server(servicer, server)
    db_service_pb2_grpc.add_ParsingServiceServicer_to_server(servicer, server)
    db_service_pb2_grpc.add_ShoppingServiceServicer_to_server(servicer, server)
    server.add_insecure_port(f"{host}:{port}")
    server.start()
    print(f"Listening on {host}:{port}")
    return server
