package com.example.grocerystoreorganizer.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.grocerystoreorganizer.data.local.entity.PackagingStyle
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.entity.ProductVariant

@Dao
interface ProductVariantDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertItems(vararg items: ProductVariant): List<Long>

    @Update
    suspend fun updateItems(vararg items: ProductVariant): Int

    @Query("select * from variants where rowid = :id")
    suspend fun FindById(id: Int): ProductVariant?

    @Query("select * from variants where productId = :productId")
    suspend fun FindAllByProduct(productId: Int): List<ProductVariant>

    @Query("select max(updatedAt) from variants where productId = :productId")
    suspend fun FindLatestUpdatedAtForProduct(productId: Int): String?

    @Query("select * from variants where upc = :upc")
    suspend fun FindByUPC(upc: String): ProductVariant?

    @Query(
        "select * from variants " +
            "where productId = :productId and label = :label and " +
            "coalesce(brand, '') = coalesce(:brand, '') and " +
            "coalesce(flavor, '') = coalesce(:flavor, '') and " +
            "coalesce(packagingStyle, '') = coalesce(:packagingStyle, '') and " +
            "packCount = :packCount " +
            "and netQuantity = :netQuantity and quantityUnit = :quantityUnit limit 1"
    )
    suspend fun FindByNaturalKey(
        productId: Int,
        label: String,
        brand: String?,
        flavor: String?,
        packagingStyle: PackagingStyle?,
        packCount: Int,
        netQuantity: Double,
        quantityUnit: ProductUnit,
    ): ProductVariant?
}
