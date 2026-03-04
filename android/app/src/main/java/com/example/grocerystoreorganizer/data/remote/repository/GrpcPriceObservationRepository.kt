package com.example.grocerystoreorganizer.data.remote.repository

import com.example.grocerystoreorganizer.data.local.repository.KnownUpcVariant
import com.example.grocerystoreorganizer.data.local.repository.PriceObservationCrudRepository
import com.example.grocerystoreorganizer.data.local.repository.PriceObservationDto
import com.example.grocerystoreorganizer.grpc.UpcRequest
import io.grpc.StatusRuntimeException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class GrpcPriceObservationRepository(
    host: String,
    port: Int,
) : PriceObservationCrudRepository {
    private val client = GroceryGrpcClient(host, port)

    override suspend fun getKnownVariantByUpc(upc: String): KnownUpcVariant? = withContext(Dispatchers.IO) {
        try {
            val response = client.resolveUpc(
                UpcRequest.newBuilder()
                    .setUpc(upc)
                    .build()
            )
            if (!response.found || !response.hasInfo()) {
                null
            } else {
                GrpcModelMapper.toKnownUpcVariant(response.info)
            }
        } catch (e: StatusRuntimeException) {
            throw IllegalStateException(e.status.description ?: "Failed to resolve UPC", e)
        }
    }

    override suspend fun insertPriceObservation(input: PriceObservationDto): Int = withContext(Dispatchers.IO) {
        try {
            val response = client.createPriceObservation(
                GrpcModelMapper.toCreateObservationRequest(input)
            )
            if (!response.hasObservationId()) {
                throw IllegalStateException("Server did not return an observation ID")
            }
            response.observationId.toInt()
        } catch (e: StatusRuntimeException) {
            if (e.status.code == io.grpc.Status.Code.ALREADY_EXISTS) {
                throw PriceObservationConflictException(
                    e.status.description ?: "UPC already exists on the server",
                    e,
                )
            }
            throw IllegalStateException(e.status.description ?: "Failed to save price observation", e)
        }
    }

    override suspend fun updatePriceObservation(observationId: Int, input: PriceObservationDto): Boolean {
        throw UnsupportedOperationException("Remote update is not implemented yet")
    }
}
