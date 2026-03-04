package com.example.grocerystoreorganizer.data.remote.repository

import com.example.grocerystoreorganizer.data.local.dao.ProductVariantDao
import com.example.grocerystoreorganizer.data.local.entity.Product
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.entity.ProductVariant

class ProductVariantCatalogRepository(
    private val variantDao: ProductVariantDao,
    private val client: GroceryGrpcClient?,
) {
    private val checkedSyncTokens = mutableMapOf<Int, String>()

    suspend fun getCachedOrFetchVariants(product: Product): List<ProductVariant> {
        val local = variantDao.FindAllByProduct(product.id)
        if (local.isNotEmpty()) {
            return local
        }
        val localSyncToken = variantDao.FindLatestUpdatedAtForProduct(product.id).orEmpty()
        if (client == null) {
            return local
        }
        if (checkedSyncTokens[product.id] == localSyncToken) {
            return local
        }

        val response = client.listVariantsForProduct(
            productName = product.name,
            updatedAfter = localSyncToken.ifEmpty { null },
        )
        response.variantsList.forEach { variant ->
            val quantityUnit = toLocalUnit(variant.quantityUnit.number)
            val existingByUpc = variantDao.FindByUPC(variant.upc)
            if (existingByUpc != null) {
                variantDao.updateItems(
                    existingByUpc.copy(
                        productId = product.id,
                        label = variant.variantLabel,
                        packCount = variant.packCount,
                        netQuantity = variant.netQuantity,
                        quantityUnit = quantityUnit,
                        isVariableWeight = variant.isVariableWeight,
                        upc = variant.upc,
                        updatedAt = variant.updatedAt,
                    )
                )
            } else {
                variantDao.insertItems(
                    ProductVariant(
                        id = 0,
                        productId = product.id,
                        label = variant.variantLabel,
                        packCount = variant.packCount,
                        netQuantity = variant.netQuantity,
                        quantityUnit = quantityUnit,
                        isVariableWeight = variant.isVariableWeight,
                        upc = variant.upc,
                        updatedAt = variant.updatedAt,
                    )
                )
            }
        }
        checkedSyncTokens[product.id] = variantDao.FindLatestUpdatedAtForProduct(product.id).orEmpty()

        return variantDao.FindAllByProduct(product.id)
    }

    private fun toLocalUnit(value: Int): ProductUnit =
        ProductUnit.entries.firstOrNull { it.ordinal == value } ?: ProductUnit.EA
}
