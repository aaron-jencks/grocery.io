package com.example.grocerystoreorganizer.ui.additem

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import com.example.grocerystoreorganizer.data.local.db.DatabaseProvider
import com.example.grocerystoreorganizer.data.local.repository.CameraRepository
import com.example.grocerystoreorganizer.data.local.repository.GroceryStoreRepository
import com.example.grocerystoreorganizer.data.local.repository.LocationRepository
import com.example.grocerystoreorganizer.data.local.source.CameraDataSource
import com.example.grocerystoreorganizer.data.local.source.LocationDataSource

class AddGroceryVmFactory(private val context: Context) : ViewModelProvider.Factory  {
    override fun <T : ViewModel> create(modelClass: Class<T>): T {
        val db = DatabaseProvider.get(context)
        val groceryRepo = GroceryStoreRepository(
            priceDao = db.priceObservationDao(),
            storeDao = db.storeDao(),
            variantDao = db.productVariantDao(),
            productDao = db.productDao(),
            saleDao = db.saleDao(),
        )
        val locationDs = LocationDataSource(context.applicationContext)
        val locationRepo = LocationRepository(locationDs)
        val cameraDs = CameraDataSource(context.applicationContext)
        val cameraRepo = CameraRepository(cameraDs)

        @Suppress("UNCHECKED_CAST")
        return AddGroceryItemViewModel(
            groceryRepo = groceryRepo,
            locationRepo = locationRepo,
            cameraRepo = cameraRepo,
            locationRequired = true,
        ) as T
    }
}
