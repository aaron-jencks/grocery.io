package com.example.grocerystoreorganizer.data.local.source

import android.content.Context
import android.content.pm.PackageManager
import android.location.Geocoder
import androidx.core.content.ContextCompat
import androidx.navigationevent.NavigationEventDispatcher
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import com.google.android.gms.tasks.CancellationTokenSource
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import java.util.Locale

class LocationDataSource(
    private val context: Context
) {
    fun hasFineLocationPermission(): Boolean =
        ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED

    suspend fun getCurrentLocation(): android.location.Location? {
        val fused = LocationServices.getFusedLocationProviderClient(context)
        val token = CancellationTokenSource()

        return try {
            withTimeoutOrNull(10_000) {
                fused.getCurrentLocation(
                    Priority.PRIORITY_HIGH_ACCURACY,
                    token.token
                ).await()
            }
        } catch (_: SecurityException) {
            null
        }
    }

    suspend fun reverseGeocode(
        lat: Double,
        lon: Double
    ): String? = withContext(Dispatchers.IO) {
        val geocoder = Geocoder(context, Locale.getDefault())
        geocoder.getFromLocation(lat, lon, 1)
            ?.firstOrNull()
            ?.getAddressLine(0)
    }
}