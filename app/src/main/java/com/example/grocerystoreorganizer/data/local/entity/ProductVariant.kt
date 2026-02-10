package com.example.grocerystoreorganizer.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "variants",
    indices = [
        Index(value = ["upc"], unique = true),
        Index(value = ["quantityUnit"]),
        Index(value = ["productId"])
    ]
)
data class ProductVariant(
    @PrimaryKey(autoGenerate = true) @ColumnInfo(name = "rowid") val id: Int,
    val productId: Int,
    val label: String,
    val packCount: Int = 1,
    val netQuantity: Double,
    val quantityUnit: ProductUnit = ProductUnit.Each,
    val isVariableWeight: Boolean = false,
    val upc: Int
)
