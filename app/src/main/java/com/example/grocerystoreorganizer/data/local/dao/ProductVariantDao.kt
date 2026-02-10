package com.example.grocerystoreorganizer.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.grocerystoreorganizer.data.local.entity.ProductVariant

@Dao
interface ProductVariantDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    fun insertItems(vararg items: ProductVariant)

    @Update
    fun updateItems(vararg items: ProductVariant)

    @Query("select * from variants where rowid = :id")
    fun FindById(id: Int): ProductVariant?

    @Query("select * from variants where productId = :productId")
    fun FindAllByProduct(productId: Int): List<ProductVariant>

    @Query("select * from variants where upc = :upc")
    fun FindByUPC(upc: Int): ProductVariant?
}