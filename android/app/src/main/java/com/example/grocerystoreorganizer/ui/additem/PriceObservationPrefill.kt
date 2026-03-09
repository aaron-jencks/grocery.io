package com.example.grocerystoreorganizer.ui.additem

import com.example.grocerystoreorganizer.data.local.entity.PackagingStyle
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit

data class PriceObservationPrefill(
    val productName: String,
    val productCategory: String? = null,
    val variantLabel: String? = null,
    val brand: String? = null,
    val flavor: String? = null,
    val packagingStyle: PackagingStyle? = null,
    val upc: String? = null,
    val packCount: Int? = null,
    val netQuantity: Double? = null,
    val quantityUnit: ProductUnit? = null,
    val isVariableWeight: Boolean = false,
)
