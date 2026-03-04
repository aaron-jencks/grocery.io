package com.example.grocerystoreorganizer.data.local.repository

interface PriceObservationCrudRepository {
    suspend fun getKnownVariantByUpc(upc: String): KnownUpcVariant?
    suspend fun insertPriceObservation(input: PriceObservationDto): Int
    suspend fun updatePriceObservation(observationId: Int, input: PriceObservationDto): Boolean
}
