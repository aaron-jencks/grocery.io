package com.example.grocerystoreorganizer.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "grocery_store_items", primaryKeys = ["store", "itemUPC"])
data class GroceryStoreItemEntity(
    val store: String,
    val itemUPC: Int,
    val itemPrice: Double,
    val itemQuantifier: GroceryItemQuantifier
)
