package com.example.grocerystoreorganizer.data.local.db

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import com.example.grocerystoreorganizer.data.local.dao.GroceryListItemDao
import com.example.grocerystoreorganizer.data.local.dao.LocalGroceryListEntryDao
import com.example.grocerystoreorganizer.data.local.dao.PriceObservationDao
import com.example.grocerystoreorganizer.data.local.dao.ProductDao
import com.example.grocerystoreorganizer.data.local.dao.ProductVariantDao
import com.example.grocerystoreorganizer.data.local.dao.SaleDao
import com.example.grocerystoreorganizer.data.local.dao.StoreDao
import com.example.grocerystoreorganizer.data.local.entity.GroceryListItem
import com.example.grocerystoreorganizer.data.local.entity.LocalGroceryListEntry
import com.example.grocerystoreorganizer.data.local.entity.PriceObservation
import com.example.grocerystoreorganizer.data.local.entity.Product
import com.example.grocerystoreorganizer.data.local.entity.ProductVariant
import com.example.grocerystoreorganizer.data.local.entity.Sale
import com.example.grocerystoreorganizer.data.local.entity.Store

@Database(
    entities = [
        Product::class,
        ProductVariant::class,
        Store::class,
        PriceObservation::class,
        Sale::class,
        GroceryListItem::class,
        LocalGroceryListEntry::class,
    ],
    version = 8
)
@TypeConverters(LocalTypeConverters::class)
abstract class LocalDatabase : RoomDatabase() {
    abstract fun productDao(): ProductDao
    abstract fun productVariantDao(): ProductVariantDao
    abstract fun storeDao(): StoreDao
    abstract fun priceObservationDao(): PriceObservationDao
    abstract fun saleDao(): SaleDao
    abstract fun groceryListItemDao(): GroceryListItemDao
    abstract fun localGroceryListEntryDao(): LocalGroceryListEntryDao
}
