package com.example.grocerystoreorganizer.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "sales")
data class Sale(
    @PrimaryKey(autoGenerate = true) @ColumnInfo("rowid") val id: Int,
    val limitQuantity: Int? = null,
    val expirationDate: String? = null,
    val startDate: String,
    val minimumQuantity: Int? = null,
)
