package com.example.grocerystoreorganizer.data.local.repository

import com.example.grocerystoreorganizer.data.local.dao.ProductDao
import com.example.grocerystoreorganizer.data.local.entity.Product
import kotlin.math.min

data class CatalogProduct(
    val name: String,
    val category: String? = null,
    val updatedAt: String,
)

class ProductCatalogRepository(
    private val productDao: ProductDao,
) {
    suspend fun syncProducts(products: List<CatalogProduct>) {
        products.forEach { product ->
            val normalizedName = normalizeName(product.name)
            if (normalizedName.isEmpty()) return@forEach
            val normalizedCategory = normalizeCategories(product.category)
            val existing = productDao.FindByName(normalizedName)
            if (existing == null) {
                productDao.insertItems(
                    Product(
                        id = 0,
                        name = normalizedName,
                        category = normalizedCategory,
                        updatedAt = product.updatedAt,
                    )
                )
            }
        }
    }

    suspend fun latestUpdatedAt(): String? = productDao.FindLatestUpdatedAt()

    suspend fun suggestProducts(query: String, limit: Int = 10): List<Product> {
        val normalizedQuery = normalizeName(query)
        if (normalizedQuery.length < 3) return emptyList()

        val queryLower = normalizedQuery.lowercase()
        return productDao.FindAll()
            .asSequence()
            .filter { it.name.isNotBlank() }
            .map { product ->
                val nameLower = product.name.lowercase()
                val startsWith = nameLower.startsWith(queryLower)
                val contains = nameLower.contains(queryLower)
                val distance = levenshteinDistance(queryLower, nameLower)
                val score = when {
                    startsWith -> distance
                    contains -> distance + 100
                    else -> distance + 200
                }
                product to score
            }
            .sortedWith(compareBy<Pair<Product, Int>> { it.second }.thenBy { it.first.name.lowercase() })
            .take(limit)
            .map { it.first }
            .toList()
    }

    private fun normalizeName(name: String): String = name.trim().lowercase()

    private fun normalizeCategories(raw: String?): String? {
        if (raw == null) return null
        val normalized = raw.split(';')
            .map { it.trim().lowercase() }
            .filter { it.isNotEmpty() }
            .distinct()
            .joinToString("; ")
        return normalized.ifBlank { null }
    }

    private fun levenshteinDistance(left: String, right: String): Int {
        if (left == right) return 0
        if (left.isEmpty()) return right.length
        if (right.isEmpty()) return left.length

        var previous = IntArray(right.length + 1) { it }
        var current = IntArray(right.length + 1)

        for (i in left.indices) {
            current[0] = i + 1
            for (j in right.indices) {
                val cost = if (left[i] == right[j]) 0 else 1
                current[j + 1] = min(
                    min(current[j] + 1, previous[j + 1] + 1),
                    previous[j] + cost,
                )
            }
            val temp = previous
            previous = current
            current = temp
        }
        return previous[right.length]
    }
}
