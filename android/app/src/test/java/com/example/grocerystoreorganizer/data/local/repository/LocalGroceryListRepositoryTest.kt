package com.example.grocerystoreorganizer.data.local.repository

import com.example.grocerystoreorganizer.data.local.dao.LocalGroceryListEntryDao
import com.example.grocerystoreorganizer.data.local.dao.ProductDao
import com.example.grocerystoreorganizer.data.local.dao.ProductVariantDao
import com.example.grocerystoreorganizer.data.local.entity.Comparison
import com.example.grocerystoreorganizer.data.local.entity.PackagingStyle
import com.example.grocerystoreorganizer.data.local.entity.LocalGroceryListEntry
import com.example.grocerystoreorganizer.data.local.entity.Product
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.entity.ProductVariant
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LocalGroceryListRepositoryTest {
    @Test
    fun addItemRejectsEmptyName() {
        runBlocking {
            val repository = LocalGroceryListRepository(FakeDao(), FakeProductDao(), FakeVariantDao())

            runCatching {
                repository.addItem(
                    name = "   ",
                    preferredVariantId = null,
                    quantityUnit = ProductUnit.EA,
                    comparisonMode = Comparison.cheapestPrice,
                )
            }
                .onSuccess { error("Expected failure") }
                .onFailure { assertTrue(it is IllegalArgumentException) }
        }
    }

    @Test
    fun moveItemUpdatesSortOrder() {
        runBlocking {
            val dao = FakeDao(
                mutableListOf(
                    LocalGroceryListEntry(1, 1, null, ProductUnit.EA, Comparison.cheapestPrice, 1, 0),
                    LocalGroceryListEntry(2, 2, null, ProductUnit.EA, Comparison.cheapestPrice, 1, 1),
                    LocalGroceryListEntry(3, 3, null, ProductUnit.EA, Comparison.cheapestPrice, 1, 2),
                )
            )
            val repository = LocalGroceryListRepository(
                dao,
                FakeProductDao(
                    mutableListOf(
                        Product(1, "Milk", null),
                        Product(2, "Bread", null),
                        Product(3, "Eggs", null),
                    )
                ),
                FakeVariantDao(),
            )

            repository.moveItem(0, 2)

            val items = dao.currentItems()
            assertEquals(listOf(2, 3, 1), items.map { it.productId })
            assertEquals(listOf(0, 1, 2), items.map { it.sortOrder })
        }
    }

    @Test
    fun decrementDesiredCountStopsAtOne() {
        runBlocking {
            val dao = FakeDao(
                mutableListOf(
                    LocalGroceryListEntry(1, 1, null, ProductUnit.EA, Comparison.cheapestPrice, 1, 0),
                )
            )
            val repository = LocalGroceryListRepository(dao, FakeProductDao(), FakeVariantDao())

            repository.decrementDesiredCount(1)

            assertEquals(1, dao.currentItems().single().desiredCount)
        }
    }

    @Test
    fun incrementDesiredCountUpdatesItem() {
        runBlocking {
            val dao = FakeDao(
                mutableListOf(
                    LocalGroceryListEntry(1, 1, null, ProductUnit.EA, Comparison.cheapestPrice, 2, 0),
                )
            )
            val repository = LocalGroceryListRepository(dao, FakeProductDao(), FakeVariantDao())

            repository.incrementDesiredCount(1)

            assertEquals(3, dao.currentItems().single().desiredCount)
        }
    }
}

private class FakeDao(
    initialItems: MutableList<LocalGroceryListEntry> = mutableListOf(),
) : LocalGroceryListEntryDao {
    private val items = initialItems
    private val flow = MutableStateFlow(toJoinedItems())

    override fun observeAll(): Flow<List<LocalGroceryListItem>> = flow

    override suspend fun findById(id: Int): LocalGroceryListEntry? = items.firstOrNull { it.id == id }

    override suspend fun findMaxSortOrder(): Int = items.maxOfOrNull { it.sortOrder } ?: -1

    override suspend fun insert(item: LocalGroceryListEntry): Long {
        val nextId = (items.maxOfOrNull { it.id } ?: 0) + 1
        items += item.copy(id = nextId)
        publish()
        return nextId.toLong()
    }

    override suspend fun updateItems(vararg items: LocalGroceryListEntry): Int {
        items.forEach { updated ->
            val index = this.items.indexOfFirst { it.id == updated.id }
            if (index >= 0) {
                this.items[index] = updated
            }
        }
        publish()
        return items.size
    }

    override suspend fun delete(item: LocalGroceryListEntry): Int {
        val removed = items.removeIf { it.id == item.id }
        publish()
        return if (removed) 1 else 0
    }

    override suspend fun clearAll(): Int {
        val count = items.size
        items.clear()
        publish()
        return count
    }

    fun currentItems(): List<LocalGroceryListEntry> =
        flow.value.map {
            LocalGroceryListEntry(
                id = it.id,
                productId = it.productId,
                preferredVariantId = it.preferredVariantId,
                quantityUnit = it.quantityUnit,
                comparisonMode = it.comparisonMode,
                desiredCount = it.desiredCount,
                sortOrder = it.sortOrder,
            )
        }

    private fun publish() {
        flow.value = toJoinedItems()
    }

    private fun toJoinedItems(): List<LocalGroceryListItem> =
        items.sortedBy { it.sortOrder }.map {
            LocalGroceryListItem(
                id = it.id,
                productId = it.productId,
                productName = "Product ${it.productId}",
                preferredVariantId = it.preferredVariantId,
                preferredVariantUpc = null,
                preferredVariantLabel = null,
                preferredVariantPackCount = null,
                preferredVariantNetQuantity = null,
                preferredVariantQuantityUnit = null,
                quantityUnit = it.quantityUnit,
                comparisonMode = it.comparisonMode,
                desiredCount = it.desiredCount,
                sortOrder = it.sortOrder,
            )
        }
}

private class FakeProductDao(
    private val items: MutableList<Product> = mutableListOf(),
) : ProductDao {
    override suspend fun insertItems(vararg items: Product): List<Long> =
        items.map { product ->
            val existing = this.items.firstOrNull { it.name == product.name }
            if (existing != null) {
                -1L
            } else {
                val nextId = (this.items.maxOfOrNull { it.id } ?: 0) + 1
                this.items += product.copy(id = nextId)
                nextId.toLong()
            }
        }

    override suspend fun updateItems(vararg items: Product): Int = items.size

    override suspend fun FindAllByCategory(category: String): List<Product> =
        items.filter { it.category == category }

    override suspend fun FindById(id: Int): Product? = items.firstOrNull { it.id == id }

    override suspend fun FindAll(): List<Product> = items.sortedBy { it.name.lowercase() }

    override suspend fun FindByName(name: String): Product? = items.firstOrNull { it.name == name }

    override suspend fun FindLatestUpdatedAt(): String? = items.maxOfOrNull { it.updatedAt }
}

private class FakeVariantDao : ProductVariantDao {
    override suspend fun insertItems(vararg items: ProductVariant): List<Long> = items.map { it.id.toLong() }

    override suspend fun updateItems(vararg items: ProductVariant): Int = items.size

    override suspend fun FindById(id: Int): ProductVariant? = null

    override suspend fun FindAllByProduct(productId: Int): List<ProductVariant> = emptyList()

    override suspend fun FindLatestUpdatedAtForProduct(productId: Int): String? = null

    override suspend fun FindByUPC(upc: String): ProductVariant? = null

    override suspend fun FindByNaturalKey(
        productId: Int,
        label: String,
        brand: String?,
        flavor: String?,
        packagingStyle: PackagingStyle?,
        packCount: Int,
        netQuantity: Double,
        quantityUnit: ProductUnit,
    ): ProductVariant? = null
}
