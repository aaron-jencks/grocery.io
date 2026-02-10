package com.example.grocerystoreorganizer.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.grocerystoreorganizer.data.local.entity.Product

@Dao
interface ProductDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    fun insertItems(vararg items: Product)

    @Update
    fun updateItems(vararg items: Product)

    @Query("select * from products where category = :category")
    fun FindAllByCategory(category: String): List<Product>

    @Query("select * from products where rowid = :id")
    fun FindById(id: Int): Product?
}