package com.example.grocerystoreorganizer.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.grocerystoreorganizer.data.local.entity.GroceryListItem
import com.example.grocerystoreorganizer.data.local.entity.Product

@Dao
interface GroceryListItemDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    fun insertItems(vararg items: GroceryListItem)

    @Update
    fun updateItems(vararg items: GroceryListItem)

    @Query("select * from list_items")
    fun FindAll(): List<GroceryListItem>

    @Query("select * from list_items where rowid = :id")
    fun FindById(id: Int): GroceryListItem?

    @Query("select * from list_items where productId = :id")
    fun FindByProduct(id: Int): GroceryListItem?
}