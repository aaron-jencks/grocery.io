package com.example.grocerystoreorganizer.data.local.repository

import com.example.grocerystoreorganizer.data.local.entity.PackagingStyle

fun buildVariantLabel(
    brand: String?,
    flavor: String?,
    packagingStyle: PackagingStyle?,
    fallback: String? = null,
): String {
    val parts = listOf(brand, flavor, packagingStyle?.display)
        .mapNotNull { it?.trim()?.takeIf(String::isNotEmpty) }
        .distinct()
    if (parts.isNotEmpty()) {
        return parts.joinToString(" ")
    }
    return fallback?.trim().orEmpty()
}
