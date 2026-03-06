package com.example.grocerystoreorganizer.data.remote.repository

import io.grpc.StatusRuntimeException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class GrpcShoppingOptimizationRepository(
    private val client: GroceryGrpcClient,
) {
    suspend fun optimize(items: List<ShoppingOptimizationItemRequest>): ShoppingOptimizationResponse =
        withContext(Dispatchers.IO) {
            try {
                val response = client.optimizeGroceryList(
                    GrpcModelMapper.toOptimizeGroceryListRequest(items)
                )
                GrpcModelMapper.toShoppingOptimizationResponse(response)
            } catch (e: StatusRuntimeException) {
                throw IllegalStateException(
                    e.status.description ?: "Failed to optimize grocery list",
                    e,
                )
            }
        }
}
