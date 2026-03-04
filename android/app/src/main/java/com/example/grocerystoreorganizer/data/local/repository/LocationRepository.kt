package com.example.grocerystoreorganizer.data.local.repository

import com.example.grocerystoreorganizer.data.local.source.LocationDataSource

class LocationRepository(
    private val dataSource: LocationDataSource
) {
    suspend fun getCurrentAddress(): LocationResult {
        if(!dataSource.hasFineLocationPermission()) return LocationResult.NoPermission
        val location = dataSource.getCurrentLocation() ?: return LocationResult.Unavailable
        val address = dataSource.reverseGeocode(location.latitude, location.longitude)
        return if(address == null) LocationResult.NoAddress else LocationResult.Success(address, location.latitude, location.longitude)
    }
}