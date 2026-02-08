package com.example.grocerystoreorganizer.data.local.dao

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.grocerystoreorganizer.data.local.entity.GroceryStoreItemEntity

@Dao
interface GroceryStoreItemDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    fun insertItems(vararg items: GroceryStoreItemEntity)

    @Update()
    fun updateItems(vararg items: GroceryStoreItemEntity)

    @Delete()
    fun deleteItems(vararg items: GroceryStoreItemEntity)

    @Query("select * from grocery_store_items where store = :store and itemUPC = :upc")
    fun getItemInformation(store: String, upc: Int): List<GroceryStoreItemEntity>

    @Query("select * from grocery_store_items where itemUPC = :upc")
    fun getAllItemStores(upc: Int): List<GroceryStoreItemEntity>
}