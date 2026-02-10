package com.example.grocerystoreorganizer.data.local.entity

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "stores")
data class Store(
    @PrimaryKey(autoGenerate = true) @ColumnInfo("rowid") val id: Int,
    val name: String? = null,
    val address: String,
    val latitude: Double,
    val longitude: Double,
)
