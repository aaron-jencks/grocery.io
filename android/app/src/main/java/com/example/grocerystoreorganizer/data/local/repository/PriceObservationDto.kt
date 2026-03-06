package com.example.grocerystoreorganizer.data.local.repository

import com.example.grocerystoreorganizer.data.local.entity.ProductUnit

data class PriceObservationDto(
    val storeAddress: String,
    val storeLatitude: Double,
    val storeLongitude: Double,
    val storeName: String? = null,
    val productName: String,
    val productCategory: String? = null,
    val variantLabel: String,
    val upc: String,
    val packCount: Int = 1,
    val netQuantity: Double,
    val quantityUnit: ProductUnit = ProductUnit.EA,
    val isVariableWeight: Boolean = false,
    val priceTotal: Double,
    val observedAt: String,
    val isSale: Boolean = false,
    val sale: SaleDto? = null,
    val trainingImageJpeg: ByteArray? = null,
    val trainingImageFilename: String? = null,
)

data class SaleDto(
    val startDate: String,
    val expirationDate: String? = null,
    val minimumQuantity: Int? = null,
    val limitQuantity: Int? = null,
)

data class ParsedPriceTagResult(
    val ambiguous: Boolean,
    val unparsable: Boolean,
    val upcParsable: Boolean,
    val upc: String? = null,
    val priceTotal: Double? = null,
    val packCount: Int? = null,
    val netQuantity: Double? = null,
    val quantityUnit: ProductUnit? = null,
    val isVariableWeight: Boolean = false,
    val message: String? = null,
)
