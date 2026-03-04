package com.example.grocerystoreorganizer.data.local.repository

import com.example.grocerystoreorganizer.data.local.entity.ProductUnit

data class KnownUpcVariant(
    val upc: String,
    val productName: String,
    val productCategory: String?,
    val variantLabel: String,
    val packCount: Int,
    val netQuantity: Double,
    val quantityUnit: ProductUnit,
    val isVariableWeight: Boolean,
)
