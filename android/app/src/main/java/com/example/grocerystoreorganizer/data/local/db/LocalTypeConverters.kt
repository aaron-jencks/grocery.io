package com.example.grocerystoreorganizer.data.local.db

import androidx.room.TypeConverter
import com.example.grocerystoreorganizer.data.local.entity.Comparison
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit

class LocalTypeConverters {
    @TypeConverter
    fun toProductUnit(value: String?): ProductUnit? =
        value?.let(ProductUnit::valueOf)

    @TypeConverter
    fun fromProductUnit(unit: ProductUnit?): String? =
        unit?.name

    @TypeConverter
    fun toComparison(value: String?): Comparison? =
        value?.let(Comparison::valueOf)

    @TypeConverter
    fun fromComparison(mode: Comparison?): String? =
        mode?.name
}
