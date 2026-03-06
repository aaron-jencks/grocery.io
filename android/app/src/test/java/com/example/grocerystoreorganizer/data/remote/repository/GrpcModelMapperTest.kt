package com.example.grocerystoreorganizer.data.remote.repository

import com.example.grocerystoreorganizer.data.local.entity.Comparison
import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.repository.PriceObservationDto
import com.example.grocerystoreorganizer.data.local.repository.SaleDto
import com.example.grocerystoreorganizer.grpc.ComparisonMode
import com.example.grocerystoreorganizer.grpc.OptimizeGroceryListResponse
import com.example.grocerystoreorganizer.grpc.OptimizedItemMatch
import com.example.grocerystoreorganizer.grpc.OptimizedStore
import com.example.grocerystoreorganizer.grpc.OptimizedVariant
import com.example.grocerystoreorganizer.grpc.ParsePriceTagImageResponse
import com.example.grocerystoreorganizer.grpc.UnmatchedOptimizationItem
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test

class GrpcModelMapperTest {
    @Test
    fun createObservationRequestMapsOptionalFields() {
        val request = GrpcModelMapper.toCreateObservationRequest(
            PriceObservationDto(
                storeAddress = "123 Main St",
                storeLatitude = 1.0,
                storeLongitude = 2.0,
                storeName = "Store",
                productName = "Milk",
                productCategory = "Dairy",
                variantLabel = "Whole",
                upc = "123456",
                packCount = 1,
                netQuantity = 64.0,
                quantityUnit = ProductUnit.OZ,
                isVariableWeight = false,
                priceTotal = 4.99,
                observedAt = "2026-03-03T10:00:00+00:00",
                isSale = true,
                sale = SaleDto(
                    startDate = "2026-03-01T00:00:00+00:00",
                    expirationDate = "2026-03-05T00:00:00+00:00",
                    minimumQuantity = 1,
                    limitQuantity = 2,
                ),
            )
        )

        assertEquals("123456", request.upc.upc)
        assertEquals("Milk", request.upc.productName)
        assertEquals(4.99, request.priceTotal, 0.0)
        assertTrue(request.hasSaleInfo())
        assertEquals(2, request.saleInfo.limitQuantity)
    }

    @Test
    fun optimizeMappingsRoundTripComparisonModes() {
        val request = GrpcModelMapper.toOptimizeGroceryListRequest(
            listOf(
                ShoppingOptimizationItemRequest(
                    itemId = 1,
                    productName = "milk",
                    desiredCount = 2,
                    comparisonMode = Comparison.bestUnitValue,
                    preferredUpc = "1234",
                )
            )
        )

        assertEquals(ComparisonMode.BEST_UNIT_VALUE, request.itemsList.first().comparisonMode)
        assertEquals("1234", request.itemsList.first().preferredUpc)

        val mapped = GrpcModelMapper.toShoppingOptimizationResponse(
            OptimizeGroceryListResponse.newBuilder()
                .addMatches(
                    OptimizedItemMatch.newBuilder()
                        .setItemId(1)
                        .setComparisonMode(ComparisonMode.CHEAPEST_PRICE)
                        .setDesiredCount(2)
                        .setStore(
                            OptimizedStore.newBuilder()
                                .setStoreId(7)
                                .setStoreName("Store")
                                .setStoreAddress("123 Main")
                                .build()
                        )
                        .setVariant(
                            OptimizedVariant.newBuilder()
                                .setUpc("1234")
                                .setProductName("milk")
                                .setVariantLabel("whole")
                                .setPackCount(1)
                                .setNetQuantity(64.0)
                                .setQuantityUnit(com.example.grocerystoreorganizer.grpc.ProductUnit.OZ)
                                .build()
                        )
                        .setPriceObservationId(9)
                        .setObservedPriceTotal(4.99)
                        .setObservedAt("2026-03-03T10:00:00+00:00")
                        .setEstimatedTotalPrice(9.98)
                        .build()
                )
                .addUnmatched(
                    UnmatchedOptimizationItem.newBuilder()
                        .setItemId(2)
                        .setProductName("bread")
                        .setReason("No price information available")
                        .build()
                )
                .build()
        )

        assertEquals(1, mapped.matches.size)
        assertEquals(Comparison.cheapestPrice, mapped.matches.first().comparisonMode)
        assertEquals(1, mapped.unmatched.size)
        assertEquals("bread", mapped.unmatched.first().productName)
    }

    @Test
    fun parsePriceTagResponseMapsOptionalFields() {
        val mapped = GrpcModelMapper.toParsedPriceTagResult(
            ParsePriceTagImageResponse.newBuilder()
                .setAmbiguous(true)
                .setUnparsable(false)
                .setUpcParsable(false)
                .setPriceTotal(3.99)
                .setPackCount(1)
                .setNetQuantity(12.0)
                .setQuantityUnit(com.example.grocerystoreorganizer.grpc.ProductUnit.TBSP)
                .setIsVariableWeight(true)
                .setMessage("partial")
                .build()
        )

        assertTrue(mapped.ambiguous)
        assertNotNull(mapped.priceTotal)
        assertEquals(3.99, mapped.priceTotal!!, 0.0)
        assertEquals(1, mapped.packCount)
        assertNotNull(mapped.netQuantity)
        assertEquals(12.0, mapped.netQuantity!!, 0.0)
        assertEquals(ProductUnit.TBSP, mapped.quantityUnit)
        assertTrue(mapped.isVariableWeight)
        assertEquals("partial", mapped.message)
    }
}
