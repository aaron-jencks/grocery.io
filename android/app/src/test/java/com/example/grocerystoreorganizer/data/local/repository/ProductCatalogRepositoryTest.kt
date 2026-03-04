package com.example.grocerystoreorganizer.data.local.repository

import com.example.grocerystoreorganizer.data.local.dao.ProductDao
import com.example.grocerystoreorganizer.data.local.entity.Product
import kotlinx.coroutines.runBlocking
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ProductCatalogRepositoryTest {
    @Test
    fun suggestProductsReturnsTopMatchesAfterThreeCharacters() {
        val repository = ProductCatalogRepository(
            FakeCatalogProductDao(
                mutableListOf(
                    Product(1, "Milk", null),
                    Product(2, "Millet", null),
                    Product(3, "Almond Milk", null),
                    Product(4, "Bread", null),
                )
            )
        )

        val suggestions = runBlocking {
            repository.suggestProducts("mil", limit = 3)
        }

        assertEquals(listOf("Milk", "Millet", "Almond Milk"), suggestions.map { it.name })
    }

    @Test
    fun syncProductsInsertsMissingProductsWithoutOverwritingExistingLocalCategory() {
        val dao = FakeCatalogProductDao(
            mutableListOf(
                Product(1, "milk", "user category", "2026-03-04T12:00:00.000000+00:00"),
            )
        )
        val repository = ProductCatalogRepository(dao)

        runBlocking {
            repository.syncProducts(
                listOf(
                    CatalogProduct(
                        name = "Milk",
                        category = "server dairy",
                        updatedAt = "2026-03-04T13:00:00.000000+00:00",
                    ),
                    CatalogProduct(
                        name = "Bread",
                        category = "bakery",
                        updatedAt = "2026-03-04T13:00:00.000000+00:00",
                    ),
                )
            )
        }

        runBlocking {
            assertEquals(2, dao.items.size)
            assertEquals("user category", dao.FindByName("milk")?.category)
            assertEquals("bakery", dao.FindByName("bread")?.category)
        }
    }
}

private class FakeCatalogProductDao(
    val items: MutableList<Product> = mutableListOf(),
) : ProductDao {
    override suspend fun insertItems(vararg items: Product): List<Long> =
        items.map { product ->
            val nextId = (this.items.maxOfOrNull { it.id } ?: 0) + 1
            this.items += product.copy(id = nextId)
            nextId.toLong()
        }

    override suspend fun updateItems(vararg items: Product): Int = items.size

    override suspend fun FindAllByCategory(category: String): List<Product> =
        items.filter { it.category == category }

    override suspend fun FindById(id: Int): Product? = items.firstOrNull { it.id == id }

    override suspend fun FindAll(): List<Product> = items.sortedBy { it.name.lowercase() }

    override suspend fun FindByName(name: String): Product? = items.firstOrNull { it.name == name }

    override suspend fun FindLatestUpdatedAt(): String? = items.maxOfOrNull { it.updatedAt }
}
