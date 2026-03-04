package com.example.grocerystoreorganizer.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "list_items",
    foreignKeys = [
        ForeignKey(
            entity = Product::class,
            parentColumns = ["rowid"],
            childColumns = ["productId"],
            onDelete = ForeignKey.CASCADE,
            onUpdate = ForeignKey.CASCADE,
        ),
        ForeignKey(
            entity = ProductVariant::class,
            parentColumns = ["rowid"],
            childColumns = ["preferredVariantId"],
            onDelete = ForeignKey.SET_NULL,
            onUpdate = ForeignKey.CASCADE,
        ),
    ],
    indices = [
        Index(value = ["productId"], unique = true),
        Index(value = ["preferredVariantId"]),
    ],
)
data class GroceryListItem(
    @PrimaryKey(autoGenerate = true) @ColumnInfo(name = "rowid") val id: Int,
    val productId: Int,
    val preferredVariantId: Int? = null,
    val quantityNeeded: Int = 1,
    val quantityUnit: ProductUnit = ProductUnit.EA,
    val comparisonMode: Comparison = Comparison.cheapestPrice
)
