package com.example.grocerystoreorganizer.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "list_items")
data class GroceryListItem(
    @PrimaryKey(autoGenerate = true) @ColumnInfo(name = "rowid") val id: Int,
    val productId: Int,
    val preferredVariantId: Int? = null,
    val quantityNeeded: Int = 1,
    val quantityUnit: ProductUnit = ProductUnit.EA,
    val comparisonMode: Comparison = Comparison.cheapestPrice
)
