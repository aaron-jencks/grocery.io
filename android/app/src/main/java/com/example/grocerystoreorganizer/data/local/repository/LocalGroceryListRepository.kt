package com.example.grocerystoreorganizer.data.local.repository

import com.example.grocerystoreorganizer.data.local.dao.LocalGroceryListEntryDao
import com.example.grocerystoreorganizer.data.local.dao.ProductDao
import com.example.grocerystoreorganizer.data.local.dao.ProductVariantDao
import com.example.grocerystoreorganizer.data.local.entity.Comparison
import com.example.grocerystoreorganizer.data.local.entity.LocalGroceryListEntry
import com.example.grocerystoreorganizer.data.local.entity.Product
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.entity.ProductVariant
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first

class LocalGroceryListRepository(
    private val dao: LocalGroceryListEntryDao,
    private val productDao: ProductDao,
    private val variantDao: ProductVariantDao,
) {
    fun observeItems(): Flow<List<LocalGroceryListItem>> = dao.observeAll()

    suspend fun getItem(id: Int): LocalGroceryListEntry? = dao.findById(id)
    suspend fun getProduct(id: Int): Product? = productDao.FindById(id)
    suspend fun findProductByName(name: String): Product? = productDao.FindByName(normalizeName(name))
    suspend fun getVariantsForProduct(productId: Int): List<ProductVariant> = variantDao.FindAllByProduct(productId)

    suspend fun addItem(
        name: String,
        preferredVariantId: Int?,
        quantityUnit: ProductUnit,
        comparisonMode: Comparison,
    ): Int {
        val normalized = normalizeName(name)
        require(normalized.isNotEmpty()) { "Item name cannot be empty" }
        val productId = resolveProductId(normalized)
        val sortOrder = dao.findMaxSortOrder() + 1
        return dao.insert(
            LocalGroceryListEntry(
                id = 0,
                productId = productId,
                preferredVariantId = preferredVariantId,
                quantityUnit = quantityUnit,
                comparisonMode = comparisonMode,
                desiredCount = 1,
                sortOrder = sortOrder,
            )
        ).toInt()
    }

    suspend fun updateItem(
        id: Int,
        name: String,
        preferredVariantId: Int?,
        quantityUnit: ProductUnit,
        comparisonMode: Comparison,
    ): Boolean {
        val normalized = normalizeName(name)
        require(normalized.isNotEmpty()) { "Item name cannot be empty" }
        val current = dao.findById(id) ?: return false
        val productId = resolveProductId(normalized)
        return dao.updateItems(
            current.copy(
                productId = productId,
                preferredVariantId = preferredVariantId,
                quantityUnit = quantityUnit,
                comparisonMode = comparisonMode,
            )
        ) > 0
    }

    suspend fun deleteItem(id: Int): Boolean {
        val current = dao.findById(id) ?: return false
        val deleted = dao.delete(current) > 0
        if (deleted) {
            normalizeSortOrder()
        }
        return deleted
    }

    suspend fun moveItem(fromIndex: Int, toIndex: Int) {
        val items = dao.observeAll().first().toMutableList()
        if (fromIndex !in items.indices || toIndex !in items.indices || fromIndex == toIndex) {
            return
        }
        val item = items.removeAt(fromIndex)
        items.add(toIndex, item)
        dao.updateItems(
            *items.mapIndexed { index, entry ->
                LocalGroceryListEntry(
                    id = entry.id,
                    productId = entry.productId,
                    preferredVariantId = entry.preferredVariantId,
                    quantityUnit = entry.quantityUnit,
                    comparisonMode = entry.comparisonMode,
                    desiredCount = entry.desiredCount,
                    sortOrder = index,
                )
            }.toTypedArray()
        )
    }

    suspend fun incrementDesiredCount(id: Int) {
        val current = dao.findById(id) ?: return
        dao.updateItems(current.copy(desiredCount = current.desiredCount + 1))
    }

    suspend fun decrementDesiredCount(id: Int) {
        val current = dao.findById(id) ?: return
        val next = (current.desiredCount - 1).coerceAtLeast(1)
        dao.updateItems(current.copy(desiredCount = next))
    }

    private suspend fun normalizeSortOrder() {
        val items = dao.observeAll().first()
        dao.updateItems(
            *items.mapIndexed { index, entry ->
                LocalGroceryListEntry(
                    id = entry.id,
                    productId = entry.productId,
                    preferredVariantId = entry.preferredVariantId,
                    quantityUnit = entry.quantityUnit,
                    comparisonMode = entry.comparisonMode,
                    desiredCount = entry.desiredCount,
                    sortOrder = index,
                )
            }.toTypedArray()
        )
    }

    private fun normalizeName(name: String): String = name.trim().lowercase()

    private suspend fun resolveProductId(name: String): Int {
        val existing = productDao.FindByName(name)
        if (existing != null) return existing.id

        val inserted = productDao.insertItems(
            Product(
                id = 0,
                name = name,
                category = null,
            )
        ).firstOrNull() ?: -1L
        if (inserted > 0L) return inserted.toInt()
        return requireNotNull(productDao.FindByName(name)).id
    }
}
