package com.example.grocerystoreorganizer.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.ForeignKey
import androidx.room.Index
import androidx.room.PrimaryKey

@Entity(
    tableName = "prices",
    foreignKeys = [
        ForeignKey(
            entity = Store::class,
            parentColumns = ["rowid"],
            childColumns = ["storeId"],
            onDelete = ForeignKey.CASCADE,
            onUpdate = ForeignKey.CASCADE,
        ),
        ForeignKey(
            entity = ProductVariant::class,
            parentColumns = ["rowid"],
            childColumns = ["variantId"],
            onDelete = ForeignKey.CASCADE,
            onUpdate = ForeignKey.CASCADE,
        ),
        ForeignKey(
            entity = Sale::class,
            parentColumns = ["rowid"],
            childColumns = ["saleId"],
            onDelete = ForeignKey.SET_NULL,
            onUpdate = ForeignKey.CASCADE,
        ),
    ],
    indices = [
        Index(value = ["observedAt", "priceTotal"]),
        Index(value = ["storeId"]),
        Index(value = ["variantId"]),
        Index(value = ["saleId"]),
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
