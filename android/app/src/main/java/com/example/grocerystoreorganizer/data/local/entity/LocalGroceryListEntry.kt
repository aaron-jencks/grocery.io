package com.example.grocerystoreorganizer.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "local_grocery_list_entries",
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
        Index(value = ["productId"]),
        Index(value = ["preferredVariantId"]),
    ],
)
data class LocalGroceryListEntry(
    @PrimaryKey(autoGenerate = true) @ColumnInfo(name = "rowid") val id: Int,
    val productId: Int,
    val preferredVariantId: Int? = null,
    val quantityUnit: ProductUnit = ProductUnit.EA,
    val comparisonMode: Comparison = Comparison.cheapestPrice,
    val desiredCount: Int = 1,
    val sortOrder: Int,
)
