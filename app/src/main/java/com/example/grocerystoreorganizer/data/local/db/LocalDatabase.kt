package com.example.grocerystoreorganizer.data.local.db

import androidx.room.Database
import androidx.room.RoomDatabase
import com.example.grocerystoreorganizer.data.local.dao.GroceryItemDao
import com.example.grocerystoreorganizer.data.local.dao.GroceryStoreDao
import com.example.grocerystoreorganizer.data.local.dao.GroceryStoreItemDao
import com.example.grocerystoreorganizer.data.local.entity.GroceryItemEntity
import com.example.grocerystoreorganizer.data.local.entity.GroceryStoreEntity
import com.example.grocerystoreorganizer.data.local.entity.GroceryStoreItemEntity

@Database(entities = [GroceryItemEntity::class, GroceryStoreEntity::class, GroceryStoreItemEntity::class], version = 1)
abstract class LocalDatabase : RoomDatabase() {
    abstract fun itemDao(): GroceryItemDao
    abstract fun storeDao(): GroceryStoreDao
    abstract fun storeItemDao(): GroceryStoreItemDao
}