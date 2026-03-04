package com.example.grocerystoreorganizer.data.local.repository

import com.example.grocerystoreorganizer.data.local.entity.Comparison
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit

data class LocalGroceryListItem(
    val id: Int,
    val productId: Int,
    val productName: String,
    val preferredVariantId: Int?,
    val preferredVariantLabel: String?,
    val preferredVariantPackCount: Int?,
    val preferredVariantNetQuantity: Double?,
    val preferredVariantQuantityUnit: ProductUnit?,
    val quantityUnit: ProductUnit,
    val comparisonMode: Comparison,
    val desiredCount: Int,
    val sortOrder: Int,
)
