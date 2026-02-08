package com.example.grocerystoreorganizer.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.grocerystoreorganizer.data.local.entity.GroceryStoreEntity

@Dao
interface GroceryStoreDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    fun insertStores(vararg stores: GroceryStoreEntity)

    @Update()
    fun updateStores(vararg stores: GroceryStoreEntity)

    @Query("select * from grocery_stores where storeAddress = :address")
    fun getStoreByAddress(address: String): List<GroceryStoreEntity>

    @Query("select * from grocery_stores")
    fun getAllStores(): List<GroceryStoreEntity>
}