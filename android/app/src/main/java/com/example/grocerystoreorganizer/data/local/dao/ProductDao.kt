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
    suspend fun insertItems(vararg items: Product): List<Long>

    @Update
    suspend fun updateItems(vararg items: Product): Int

    @Query("select * from products where lower(category) = lower(:category)")
    suspend fun FindAllByCategory(category: String): List<Product>

    @Query("select * from products where rowid = :id")
    suspend fun FindById(id: Int): Product?

    @Query("select * from products order by name collate nocase asc")
    suspend fun FindAll(): List<Product>

    @Query("select * from products where lower(name) = lower(:name) limit 1")
    suspend fun FindByName(name: String): Product?

    @Query("select max(updatedAt) from products")
    suspend fun FindLatestUpdatedAt(): String?
}
