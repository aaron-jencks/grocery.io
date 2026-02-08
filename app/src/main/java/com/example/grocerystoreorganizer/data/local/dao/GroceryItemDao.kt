package com.example.grocerystoreorganizer.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.grocerystoreorganizer.data.local.entity.GroceryItemEntity

@Dao
interface GroceryItemDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    fun insertItems(vararg items: GroceryItemEntity)

    @Update
    fun updateItems(vararg items: GroceryItemEntity)

    @Query("select * from grocery_items where itemUPC = :upc")
    fun getItemByUPC(upc: Int): List<GroceryItemEntity>
}