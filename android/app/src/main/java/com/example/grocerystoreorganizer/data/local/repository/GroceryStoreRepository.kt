package com.example.grocerystoreorganizer.data.local.repository

import com.example.grocerystoreorganizer.data.local.dao.PriceObservationDao
import com.example.grocerystoreorganizer.data.local.dao.ProductDao
import com.example.grocerystoreorganizer.data.local.dao.ProductVariantDao
import com.example.grocerystoreorganizer.data.local.dao.SaleDao
import com.example.grocerystoreorganizer.data.local.dao.StoreDao
import com.example.grocerystoreorganizer.data.local.entity.PriceObservation
import com.example.grocerystoreorganizer.data.local.entity.Product
import com.example.grocerystoreorganizer.data.local.entity.ProductVariant
import com.example.grocerystoreorganizer.data.local.entity.Sale
import com.example.grocerystoreorganizer.data.local.entity.Store

class GroceryStoreRepository(
    private val priceDao: PriceObservationDao,
    private val storeDao: StoreDao,
    private val variantDao: ProductVariantDao,
    private val productDao: ProductDao,
    private val saleDao: SaleDao,
) : PriceObservationCrudRepository {
    override suspend fun getKnownVariantByUpc(upc: String): KnownUpcVariant? {
        val variant = variantDao.FindByUPC(upc) ?: return null
        val product = productDao.FindById(variant.productId) ?: return null
        return KnownUpcVariant(
            upc = variant.upc,
            productName = product.name,
            productCategory = product.category,
            variantLabel = variant.label,
            packCount = variant.packCount,
            netQuantity = variant.netQuantity,
            quantityUnit = variant.quantityUnit,
            isVariableWeight = variant.isVariableWeight,
        )
    }

    override suspend fun insertPriceObservation(input: PriceObservationDto): Int {
        validateInput(input)

        val storeId = resolveStoreId(input)
        val productId = resolveProductId(input)
        val variantId = resolveVariantId(input, productId)
        val saleId = resolveSaleId(input)

        val item = PriceObservation(
            id = 0,
            storeId = storeId,
            variantId = variantId,
            priceTotal = input.priceTotal,
            observedAt = input.observedAt,
            isSale = input.isSale,
            saleId = saleId,
        )
        val inserted = priceDao.insertItems(item).firstOrNull() ?: -1L
        check(inserted > 0L) { "Failed to insert price observation" }
        return inserted.toInt()
    }

    override suspend fun updatePriceObservation(
        observationId: Int,
        input: PriceObservationDto,
    ): Boolean {
        validateInput(input)
        val current = priceDao.FindById(observationId) ?: return false

        val storeId = resolveStoreId(input)
        val productId = resolveProductId(input)
        val variantId = resolveVariantId(input, productId)
        val saleId = resolveSaleId(input)

        val updated = current.copy(
            storeId = storeId,
            variantId = variantId,
            priceTotal = input.priceTotal,
            observedAt = input.observedAt,
            isSale = input.isSale,
            saleId = saleId,
        )
        return priceDao.updateItems(updated) > 0
    }

    private suspend fun resolveStoreId(input: PriceObservationDto): Int {
        val existing = storeDao.FindByAddress(input.storeAddress)
        if (existing != null) {
            val updated = existing.copy(
                name = input.storeName ?: existing.name,
                latitude = input.storeLatitude,
                longitude = input.storeLongitude,
            )
            if (updated != existing) {
                storeDao.updateItems(updated)
            }
            return existing.id
        }

        val inserted = storeDao.insertItems(
            Store(
                id = 0,
                name = input.storeName,
                address = input.storeAddress,
                latitude = input.storeLatitude,
                longitude = input.storeLongitude,
            )
        ).firstOrNull() ?: -1L
        if (inserted > 0L) return inserted.toInt()
        return requireNotNull(storeDao.FindByAddress(input.storeAddress)).id
    }

    private suspend fun resolveProductId(input: PriceObservationDto): Int {
        val normalizedCategory = normalizeCategories(input.productCategory)
        val existing = productDao.FindByName(input.productName)
        if (existing != null) {
            val updated = existing.copy(
                category = normalizedCategory ?: existing.category,
            )
            if (updated != existing) {
                productDao.updateItems(updated)
            }
            return existing.id
        }

        val inserted = productDao.insertItems(
            Product(
                id = 0,
                name = input.productName,
                category = normalizedCategory,
            )
        ).firstOrNull() ?: -1L
        if (inserted > 0L) return inserted.toInt()
        return requireNotNull(productDao.FindByName(input.productName)).id
    }

    private suspend fun resolveVariantId(input: PriceObservationDto, productId: Int): Int {
        variantDao.FindByUPC(input.upc)?.let { byUpc ->
            if (byUpc.productId != productId) {
                throw IllegalArgumentException(
                    "UPC ${input.upc} already exists for a different productId=${byUpc.productId}"
                )
            }
            val updated = byUpc.copy(
                label = input.variantLabel,
                packCount = input.packCount,
                netQuantity = input.netQuantity,
                quantityUnit = input.quantityUnit,
                isVariableWeight = input.isVariableWeight,
            )
            if (updated != byUpc) {
                variantDao.updateItems(updated)
            }
            return byUpc.id
        }

        variantDao.FindByNaturalKey(
            productId = productId,
            label = input.variantLabel,
            packCount = input.packCount,
            netQuantity = input.netQuantity,
            quantityUnit = input.quantityUnit,
        )?.let { natural ->
            return natural.id
        }

        val inserted = variantDao.insertItems(
            ProductVariant(
                id = 0,
                productId = productId,
                label = input.variantLabel,
                packCount = input.packCount,
                netQuantity = input.netQuantity,
                quantityUnit = input.quantityUnit,
                isVariableWeight = input.isVariableWeight,
                upc = input.upc,
            )
        ).firstOrNull() ?: -1L
        if (inserted > 0L) return inserted.toInt()
        return requireNotNull(variantDao.FindByUPC(input.upc)).id
    }

    private suspend fun resolveSaleId(input: PriceObservationDto): Int? {
        if (!input.isSale) return null
        val saleInput = input.sale
        val startDate = saleInput?.startDate ?: input.observedAt

        val inserted = saleDao.insertItems(
            Sale(
                id = 0,
                limitQuantity = saleInput?.limitQuantity,
                expirationDate = saleInput?.expirationDate,
                startDate = startDate,
                minimumQuantity = saleInput?.minimumQuantity,
            )
        ).firstOrNull() ?: -1L
        check(inserted > 0L) { "Failed to insert sale details" }
        return inserted.toInt()
    }

    private fun validateInput(input: PriceObservationDto) {
        require(input.storeAddress.isNotBlank()) { "Store address is required" }
        require(input.productName.isNotBlank()) { "Product name is required" }
        require(input.variantLabel.isNotBlank()) { "Variant label is required" }
        require(input.upc.all { it.isDigit() }) { "UPC must contain only digits" }
        require(input.upc.length >= 4) { "UPC must be at least 4 digits" }
        require(input.packCount > 0) { "Pack count must be greater than zero" }
        require(input.netQuantity > 0.0) { "Net quantity must be greater than zero" }
        require(input.priceTotal >= 0.0) { "Price must be non-negative" }
        require(input.observedAt.isNotBlank()) { "observedAt is required" }
    }

    private fun normalizeCategories(raw: String?): String? {
        if (raw == null) return null
        val normalized = raw.split(';')
            .map { it.trim() }
            .filter { it.isNotEmpty() }
            .distinct()
            .joinToString("; ")
        return normalized.ifBlank { null }
    }
}
