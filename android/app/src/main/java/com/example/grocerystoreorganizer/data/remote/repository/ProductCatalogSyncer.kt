package com.example.grocerystoreorganizer.data.remote.repository

import com.example.grocerystoreorganizer.data.local.repository.CatalogProduct
import com.example.grocerystoreorganizer.data.local.repository.ProductCatalogRepository
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class ProductCatalogSyncer(
    private val client: GroceryGrpcClient,
    private val productCatalogRepository: ProductCatalogRepository,
) {
    suspend fun syncFromServer() = withContext(Dispatchers.IO) {
        val response = client.listProducts(productCatalogRepository.latestUpdatedAt())
        val products = response.productsList.map { product ->
            CatalogProduct(
                name = product.productName,
                category = if (product.hasProductCategory()) product.productCategory else null,
                updatedAt = product.updatedAt,
            )
        }
        productCatalogRepository.syncProducts(products)
    }
}
