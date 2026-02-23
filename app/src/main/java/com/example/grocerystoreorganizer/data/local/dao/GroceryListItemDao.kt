package com.example.grocerystoreorganizer.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.grocerystoreorganizer.data.local.entity.GroceryListItem

@Dao
interface GroceryListItemDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertItems(vararg items: GroceryListItem): List<Long>

    @Update
    suspend fun updateItems(vararg items: GroceryListItem): Int

    @Query("select * from list_items")
    suspend fun FindAll(): List<GroceryListItem>

    @Query("select * from list_items where rowid = :id")
    suspend fun FindById(id: Int): GroceryListItem?

    @Query("select * from list_items where productId = :id")
    suspend fun FindByProduct(id: Int): GroceryListItem?
}
