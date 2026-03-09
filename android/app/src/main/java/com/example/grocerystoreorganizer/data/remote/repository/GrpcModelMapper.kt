package com.example.grocerystoreorganizer.data.remote.repository

import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.entity.Comparison
import com.example.grocerystoreorganizer.data.local.entity.PackagingStyle
import com.example.grocerystoreorganizer.data.local.repository.KnownUpcVariant
import com.example.grocerystoreorganizer.data.local.repository.ParsedPriceTagResult
import com.example.grocerystoreorganizer.data.local.repository.PriceObservationDto
import com.example.grocerystoreorganizer.data.local.repository.buildVariantLabel
import com.example.grocerystoreorganizer.grpc.ComparisonMode
import com.example.grocerystoreorganizer.grpc.Coordinate
import com.example.grocerystoreorganizer.grpc.GroceryListOptimizationItem
import com.example.grocerystoreorganizer.grpc.OptimizeGroceryListRequest
import com.example.grocerystoreorganizer.grpc.OptimizeGroceryListResponse
import com.example.grocerystoreorganizer.grpc.ParsePriceTagImageResponse
import com.example.grocerystoreorganizer.grpc.PackagingStyle as GrpcPackagingStyle
import com.example.grocerystoreorganizer.grpc.PriceObservationRequest
import com.example.grocerystoreorganizer.grpc.ProductUnit as GrpcProductUnit
import com.example.grocerystoreorganizer.grpc.SaleInfo
import com.example.grocerystoreorganizer.grpc.StoreInfo
import com.example.grocerystoreorganizer.grpc.UpcInfo
import com.google.protobuf.ByteString

internal object GrpcModelMapper {
    fun toKnownUpcVariant(info: UpcInfo): KnownUpcVariant =
        KnownUpcVariant(
            upc = info.upc,
            productName = info.productName,
            productCategory = if (info.hasProductCategory()) info.productCategory else null,
            variantLabel = buildVariantLabel(
                brand = if (info.hasBrand()) info.brand else null,
                flavor = if (info.hasFlavor()) info.flavor else null,
                packagingStyle = if (info.hasPackagingStyle()) toLocalPackagingStyle(info.packagingStyle) else null,
                fallback = info.variantLabel,
            ),
            brand = if (info.hasBrand()) info.brand else null,
            flavor = if (info.hasFlavor()) info.flavor else null,
            packagingStyle = if (info.hasPackagingStyle()) toLocalPackagingStyle(info.packagingStyle) else null,
            packCount = info.packCount,
            netQuantity = info.netQuantity,
            quantityUnit = toLocalUnit(info.quantityUnit),
            isVariableWeight = info.isVariableWeight,
        )

    fun toCreateObservationRequest(input: PriceObservationDto): PriceObservationRequest {
        val upcBuilder = UpcInfo.newBuilder()
            .setUpc(input.upc)
            .setProductName(input.productName)
            .setVariantLabel(input.variantLabel)
            .setPackCount(input.packCount)
            .setNetQuantity(input.netQuantity)
            .setQuantityUnit(toGrpcUnit(input.quantityUnit))
            .setIsVariableWeight(input.isVariableWeight)
        input.productCategory?.let(upcBuilder::setProductCategory)
        input.brand?.let(upcBuilder::setBrand)
        input.flavor?.let(upcBuilder::setFlavor)
        input.packagingStyle?.let { upcBuilder.packagingStyle = toGrpcPackagingStyle(it) }

        val storeBuilder = StoreInfo.newBuilder()
            .setStoreAddress(input.storeAddress)
            .setLocation(
                Coordinate.newBuilder()
                    .setLatitude(input.storeLatitude)
                    .setLongitude(input.storeLongitude)
                    .build()
            )
        input.storeName?.let(storeBuilder::setStoreName)

        val requestBuilder = PriceObservationRequest.newBuilder()
            .setStore(storeBuilder.build())
            .setUpc(upcBuilder.build())
            .setPriceTotal(input.priceTotal)
            .setObservedAt(input.observedAt)
            .setIsSale(input.isSale)

        input.sale?.let { sale ->
            requestBuilder.saleInfo = SaleInfo.newBuilder()
                .setStartDate(sale.startDate)
                .apply {
                    sale.expirationDate?.let(::setExpirationDate)
                    sale.minimumQuantity?.let(::setMinimumQuantity)
                    sale.limitQuantity?.let(::setLimitQuantity)
                }
                .build()
        }
        input.trainingImageJpeg?.let { jpeg ->
            requestBuilder.trainingImageJpeg = ByteString.copyFrom(jpeg)
        }
        input.trainingImageFilename?.let(requestBuilder::setTrainingImageFilename)
        input.trainingImageUpcPresent?.let(requestBuilder::setTrainingImageUpcPresent)

        return requestBuilder.build()
    }

    fun toOptimizeGroceryListRequest(
        items: List<ShoppingOptimizationItemRequest>
    ): OptimizeGroceryListRequest =
        OptimizeGroceryListRequest.newBuilder()
            .addAllItems(
                items.map { item ->
                    GroceryListOptimizationItem.newBuilder()
                        .setItemId(item.itemId)
                        .setProductName(item.productName)
                        .setDesiredCount(item.desiredCount)
                        .setComparisonMode(toGrpcComparison(item.comparisonMode))
                        .apply { item.preferredUpc?.let(::setPreferredUpc) }
                        .build()
                }
            )
            .build()

    fun toShoppingOptimizationResponse(
        response: OptimizeGroceryListResponse
    ): ShoppingOptimizationResponse =
        ShoppingOptimizationResponse(
            matches = response.matchesList.map { match ->
                ShoppingOptimizationMatch(
                    itemId = match.itemId,
                    comparisonMode = toLocalComparison(match.comparisonMode),
                    desiredCount = match.desiredCount,
                    storeId = match.store.storeId.toInt(),
                    storeName = if (match.store.hasStoreName()) match.store.storeName else null,
                    storeAddress = match.store.storeAddress,
                    variantUpc = match.variant.upc,
                    variantProductName = match.variant.productName,
                    variantLabel = match.variant.variantLabel,
                    variantBrand = if (match.variant.hasBrand()) match.variant.brand else null,
                    variantFlavor = if (match.variant.hasFlavor()) match.variant.flavor else null,
                    variantPackagingStyle = if (match.variant.hasPackagingStyle()) toLocalPackagingStyle(match.variant.packagingStyle) else null,
                    variantPackCount = match.variant.packCount,
                    variantNetQuantity = match.variant.netQuantity,
                    variantQuantityUnit = toLocalUnit(match.variant.quantityUnit),
                    priceObservationId = match.priceObservationId.toInt(),
                    observedPriceTotal = match.observedPriceTotal,
                    observedAt = match.observedAt,
                    estimatedTotalPrice = match.estimatedTotalPrice,
                )
            },
            unmatched = response.unmatchedList.map { item ->
                ShoppingOptimizationUnmatched(
                    itemId = item.itemId,
                    productName = item.productName,
                    reason = item.reason,
                )
            },
        )

    fun toParsedPriceTagResult(response: ParsePriceTagImageResponse): ParsedPriceTagResult =
        ParsedPriceTagResult(
            ambiguous = response.ambiguous,
            unparsable = response.unparsable,
            upcParsable = response.upcParsable,
            upc = if (response.hasUpc()) response.upc else null,
            priceTotal = if (response.hasPriceTotal()) response.priceTotal else null,
            packCount = if (response.hasPackCount()) response.packCount else null,
            netQuantity = if (response.hasNetQuantity()) response.netQuantity else null,
            quantityUnit = if (response.hasQuantityUnit()) toLocalUnit(response.quantityUnit) else null,
            isVariableWeight = response.isVariableWeight,
            message = if (response.hasMessage()) response.message else null,
        )

    private fun toGrpcUnit(unit: ProductUnit): GrpcProductUnit =
        when (unit) {
            ProductUnit.OZ -> GrpcProductUnit.OZ
            ProductUnit.LB -> GrpcProductUnit.LB
            ProductUnit.EA -> GrpcProductUnit.EA
            ProductUnit.KG -> GrpcProductUnit.KG
            ProductUnit.G -> GrpcProductUnit.G
            ProductUnit.LIT -> GrpcProductUnit.LIT
            ProductUnit.ML -> GrpcProductUnit.ML
            ProductUnit.GAL -> GrpcProductUnit.GAL
            ProductUnit.QT -> GrpcProductUnit.QT
            ProductUnit.PT -> GrpcProductUnit.PT
            ProductUnit.TSP -> GrpcProductUnit.TSP
            ProductUnit.TBSP -> GrpcProductUnit.TBSP
        }

    private fun toGrpcComparison(comparison: Comparison): ComparisonMode =
        when (comparison) {
            Comparison.cheapestPrice -> ComparisonMode.CHEAPEST_PRICE
            Comparison.bestUnitValue -> ComparisonMode.BEST_UNIT_VALUE
        }

    private fun toLocalComparison(comparison: ComparisonMode): Comparison =
        when (comparison) {
            ComparisonMode.BEST_UNIT_VALUE -> Comparison.bestUnitValue
            else -> Comparison.cheapestPrice
        }

    private fun toLocalUnit(unit: GrpcProductUnit): ProductUnit =
        when (unit) {
            GrpcProductUnit.OZ -> ProductUnit.OZ
            GrpcProductUnit.LB -> ProductUnit.LB
            GrpcProductUnit.EA -> ProductUnit.EA
            GrpcProductUnit.KG -> ProductUnit.KG
            GrpcProductUnit.G -> ProductUnit.G
            GrpcProductUnit.LIT -> ProductUnit.LIT
            GrpcProductUnit.ML -> ProductUnit.ML
            GrpcProductUnit.GAL -> ProductUnit.GAL
            GrpcProductUnit.QT -> ProductUnit.QT
            GrpcProductUnit.PT -> ProductUnit.PT
            GrpcProductUnit.TSP -> ProductUnit.TSP
            GrpcProductUnit.TBSP -> ProductUnit.TBSP
            GrpcProductUnit.ITEM -> ProductUnit.EA
            else -> ProductUnit.EA
        }

    private fun toGrpcPackagingStyle(value: PackagingStyle): GrpcPackagingStyle =
        when (value) {
            PackagingStyle.LOOSE -> GrpcPackagingStyle.LOOSE
            PackagingStyle.CAN -> GrpcPackagingStyle.CAN
            PackagingStyle.BOTTLE -> GrpcPackagingStyle.BOTTLE
            PackagingStyle.BOX -> GrpcPackagingStyle.BOX
            PackagingStyle.BAG -> GrpcPackagingStyle.BAG
            PackagingStyle.CARTON -> GrpcPackagingStyle.CARTON
            PackagingStyle.BUNCH -> GrpcPackagingStyle.BUNCH
            PackagingStyle.OTHER -> GrpcPackagingStyle.OTHER
        }

    private fun toLocalPackagingStyle(value: GrpcPackagingStyle): PackagingStyle? =
        when (value) {
            GrpcPackagingStyle.LOOSE -> PackagingStyle.LOOSE
            GrpcPackagingStyle.CAN -> PackagingStyle.CAN
            GrpcPackagingStyle.BOTTLE -> PackagingStyle.BOTTLE
            GrpcPackagingStyle.BOX -> PackagingStyle.BOX
            GrpcPackagingStyle.BAG -> PackagingStyle.BAG
            GrpcPackagingStyle.CARTON -> PackagingStyle.CARTON
            GrpcPackagingStyle.BUNCH -> PackagingStyle.BUNCH
            GrpcPackagingStyle.OTHER -> PackagingStyle.OTHER
            else -> null
        }
}
