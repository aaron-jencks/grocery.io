package com.example.grocerystoreorganizer.data.local.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "grocery_items")
data class GroceryItemEntity(
    @PrimaryKey val itemUPC: Int,
    val itemDescription: String
)
