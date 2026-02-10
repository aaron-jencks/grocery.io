package com.example.grocerystoreorganizer.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "prices",
    indices = [
        Index(value = ["observedAt", "priceTotal"]),
        Index(value = ["storeId"]),
    ]
)
data class PriceObservation(
    @PrimaryKey(autoGenerate = true) @ColumnInfo(name = "rowid") val id: Int,
    val storeId: Int,
    val variantId: Int,
    val priceTotal: Double,
    val observedAt: String,
    val isSale: Boolean = false,
    val saleId: Int? = null,
)
