package com.example.grocerystoreorganizer.data.remote.repository

import com.example.grocerystoreorganizer.data.local.entity.ProductUnit
import com.example.grocerystoreorganizer.data.local.repository.PriceObservationDto
import com.example.grocerystoreorganizer.data.local.repository.SaleDto
import org.junit.Assert.assertEquals
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
}
