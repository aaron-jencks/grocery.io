package com.example.grocerystoreorganizer.ui.additem

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.example.grocerystoreorganizer.data.local.db.DatabaseProvider
import com.example.grocerystoreorganizer.data.local.repository.GroceryStoreRepository
import com.example.grocerystoreorganizer.data.local.repository.LocationRepository
import com.example.grocerystoreorganizer.data.local.source.LocationDataSource

class AddGroceryVmFactory(private val context: Context) : ViewModelProvider.Factory  {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        val db = DatabaseProvider.get(context)
        val groceryRepo = GroceryStoreRepository(db.itemDao(), db.storeDao(), db.storeItemDao())
        val locationDs = LocationDataSource(context.applicationContext)
        val locationRepo = LocationRepository(locationDs)

        @Suppress("UNCHECKED_CAST")
        return AddGroceryItemViewModel(
            groceryRepo = groceryRepo,
            locationRepo = locationRepo,
            locationRequired = true,
        ) as T
    }
}