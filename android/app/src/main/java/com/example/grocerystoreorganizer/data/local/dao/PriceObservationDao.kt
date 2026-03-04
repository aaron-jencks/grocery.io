package com.example.grocerystoreorganizer.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.grocerystoreorganizer.data.local.entity.PriceObservation

@Dao
interface PriceObservationDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertItems(vararg items: PriceObservation): List<Long>

    @Update
    suspend fun updateItems(vararg items: PriceObservation): Int

    @Query("select * from prices where rowid = :id")
    suspend fun FindById(id: Int): PriceObservation?

    @Query("select * from prices where storeId = :storeId")
    suspend fun FindAllByStore(storeId: Int): List<PriceObservation>

    @Query("select prices.* from prices left join variants on prices.variantId = variants.rowid where variants.productId = :productId")
    suspend fun FindAllByProduct(productId: Int): List<PriceObservation>

    @Query("select prices.* from prices left join variants on prices.variantId = variants.rowid where variants.productId = :productId and prices.storeId = :storeId")
    suspend fun FindAllByProductAndStore(productId: Int, storeId: Int): List<PriceObservation>
}
