package com.example.grocerystoreorganizer.data.remote.repository

import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.repository.KnownUpcVariant
import com.example.grocerystoreorganizer.data.local.repository.PriceObservationDto
import com.example.grocerystoreorganizer.grpc.Coordinate
import com.example.grocerystoreorganizer.grpc.PriceObservationRequest
import com.example.grocerystoreorganizer.grpc.ProductUnit as GrpcProductUnit
import com.example.grocerystoreorganizer.grpc.SaleInfo
import com.example.grocerystoreorganizer.grpc.StoreInfo
import com.example.grocerystoreorganizer.grpc.UpcInfo

internal object GrpcModelMapper {
    fun toKnownUpcVariant(info: UpcInfo): KnownUpcVariant =
        KnownUpcVariant(
            upc = info.upc,
            productName = info.productName,
            productCategory = if (info.hasProductCategory()) info.productCategory else null,
            variantLabel = info.variantLabel,
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

        return requestBuilder.build()
    }

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
            else -> ProductUnit.EA
        }
}
