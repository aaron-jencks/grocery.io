package com.example.grocerystoreorganizer.data.remote.repository

import com.example.grocerystoreorganizer.data.local.dao.ProductVariantDao
import com.example.grocerystoreorganizer.data.local.entity.PackagingStyle
import com.example.grocerystoreorganizer.data.local.entity.Product
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.entity.ProductVariant
import com.example.grocerystoreorganizer.grpc.ListVariantsForProductResponse
import com.example.grocerystoreorganizer.grpc.UpcInfo
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class ProductVariantCatalogRepositoryTest {
    @Test
    fun returnsCachedVariantsWithoutCallingServer() {
        val product = Product(id = 7, name = "milk")
        val variant = ProductVariant(
            id = 1,
            productId = product.id,
            label = "whole",
            packCount = 1,
            netQuantity = 64.0,
            quantityUnit = ProductUnit.OZ,
            isVariableWeight = false,
            upc = "1234",
        )
        val dao = FakeProductVariantDao(mutableListOf(variant))
        val client = FakeGroceryGrpcClient(
            responses = mapOf(product.name to emptyList()),
        )
        val repository = ProductVariantCatalogRepository(dao, client)

        val result = runBlocking { repository.getCachedOrFetchVariants(product) }

        assertEquals(listOf(variant), result)
        assertTrue(client.requestedProducts.isEmpty())
    }

    @Test
    fun fetchesAndCachesVariantsWhenLocalDatabaseIsEmpty() {
        val product = Product(id = 9, name = "chips")
        val dao = FakeProductVariantDao()
        val client = FakeGroceryGrpcClient(
            responses = mapOf(
                product.name to listOf(
                    UpcInfo.newBuilder()
                        .setUpc("9999")
                        .setProductName(product.name)
                        .setVariantLabel("salted")
                        .setPackCount(1)
                        .setNetQuantity(8.0)
                        .setQuantityUnit(com.example.grocerystoreorganizer.grpc.ProductUnit.OZ)
                        .setIsVariableWeight(false)
                        .setUpdatedAt("2026-03-04T12:00:00.000000+00:00")
                        .build()
                )
            )
        )
        val repository = ProductVariantCatalogRepository(dao, client)

        val first = runBlocking { repository.getCachedOrFetchVariants(product) }
        val second = runBlocking { repository.getCachedOrFetchVariants(product) }

        assertEquals(1, first.size)
        assertEquals("salted", first.single().label)
        assertEquals(first, second)
        assertEquals(listOf(product.name), client.requestedProducts)
    }

    @Test
    fun cachesEmptyServerResponsesForSession() {
        val product = Product(id = 11, name = "unknown")
        val dao = FakeProductVariantDao()
        val client = FakeGroceryGrpcClient(
            responses = mapOf(product.name to emptyList()),
        )
        val repository = ProductVariantCatalogRepository(dao, client)

        runBlocking { repository.getCachedOrFetchVariants(product) }
        runBlocking { repository.getCachedOrFetchVariants(product) }

        assertEquals(listOf(product.name), client.requestedProducts)
    }
}

private class FakeProductVariantDao(
    initialItems: MutableList<ProductVariant> = mutableListOf(),
) : ProductVariantDao {
    private val items = initialItems

    override suspend fun insertItems(vararg items: ProductVariant): List<Long> =
        items.map { variant ->
            val nextId = (this.items.maxOfOrNull { it.id } ?: 0) + 1
            this.items += variant.copy(id = nextId)
            nextId.toLong()
        }

    override suspend fun updateItems(vararg items: ProductVariant): Int {
        items.forEach { updated ->
            val index = this.items.indexOfFirst { it.id == updated.id }
            if (index >= 0) {
                this.items[index] = updated
            }
        }
        return items.size
    }

    override suspend fun FindById(id: Int): ProductVariant? = items.firstOrNull { it.id == id }

    override suspend fun FindAllByProduct(productId: Int): List<ProductVariant> =
        items.filter { it.productId == productId }

    override suspend fun FindLatestUpdatedAtForProduct(productId: Int): String? =
        items.filter { it.productId == productId }.maxOfOrNull { it.updatedAt }

    override suspend fun FindByUPC(upc: String): ProductVariant? =
        items.firstOrNull { it.upc == upc }

    override suspend fun FindByNaturalKey(
        productId: Int,
        label: String,
        brand: String?,
        flavor: String?,
        packagingStyle: PackagingStyle?,
        packCount: Int,
        netQuantity: Double,
        quantityUnit: ProductUnit,
    ): ProductVariant? =
        items.firstOrNull {
            it.productId == productId &&
                it.label == label &&
                it.brand == brand &&
                it.flavor == flavor &&
                it.packagingStyle == packagingStyle &&
                it.packCount == packCount &&
                it.netQuantity == netQuantity &&
                it.quantityUnit == quantityUnit
        }
}

private class FakeGroceryGrpcClient(
    private val responses: Map<String, List<UpcInfo>>,
) : GroceryGrpcClient("localhost", 1) {
    val requestedProducts = mutableListOf<String>()

    override fun listVariantsForProduct(
        productName: String,
        updatedAfter: String?,
    ): ListVariantsForProductResponse {
        requestedProducts += productName
        return ListVariantsForProductResponse.newBuilder()
            .addAllVariants(responses[productName].orEmpty())
            .build()
    }

    override fun shutdown() {
    }
}
