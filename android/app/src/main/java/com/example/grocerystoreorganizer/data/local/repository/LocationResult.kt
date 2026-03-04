package com.example.grocerystoreorganizer.data.local.repository

sealed interface LocationResult {
    data class Success(val address: String, val latitude: Double, val longitude: Double) : LocationResult
    data object NoAddress : LocationResult
    data object NoPermission : LocationResult
    data object Unavailable : LocationResult
    data class Error(val message: String) : LocationResult
}