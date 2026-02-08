package com.example.grocerystoreorganizer.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "grocery_stores")
data class GroceryStoreEntity(
    @PrimaryKey val storeAddress: String,
    val storeLat: Double,
    val storeLong: Double,
)
