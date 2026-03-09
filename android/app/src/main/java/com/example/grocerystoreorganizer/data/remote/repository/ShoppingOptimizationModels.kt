package com.example.grocerystoreorganizer.data.remote.repository

import com.example.grocerystoreorganizer.data.local.entity.Comparison
import com.example.grocerystoreorganizer.data.local.entity.PackagingStyle
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit

data class ShoppingOptimizationItemRequest(
    val itemId: Int,
    val productName: String,
    val desiredCount: Int,
    val comparisonMode: Comparison,
    val preferredUpc: String?,
)

data class ShoppingOptimizationMatch(
    val itemId: Int,
    val comparisonMode: Comparison,
    val desiredCount: Int,
    val storeId: Int,
    val storeName: String?,
    val storeAddress: String,
    val variantUpc: String,
    val variantProductName: String,
    val variantLabel: String,
    val variantBrand: String?,
    val variantFlavor: String?,
    val variantPackagingStyle: PackagingStyle?,
    val variantPackCount: Int,
    val variantNetQuantity: Double,
    val variantQuantityUnit: ProductUnit,
    val priceObservationId: Int,
    val observedPriceTotal: Double,
    val observedAt: String,
    val estimatedTotalPrice: Double,
)

data class ShoppingOptimizationUnmatched(
    val itemId: Int,
    val productName: String,
    val reason: String,
)

data class ShoppingOptimizationResponse(
    val matches: List<ShoppingOptimizationMatch>,
    val unmatched: List<ShoppingOptimizationUnmatched>,
)
