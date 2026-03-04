package com.example.grocerystoreorganizer.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.grocerystoreorganizer.data.local.entity.Store

@Dao
interface StoreDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertItems(vararg items: Store): List<Long>

    @Update
    suspend fun updateItems(vararg items: Store): Int

    @Query("select * from stores where rowid = :id")
    suspend fun FindById(id: Int): Store?

    @Query("select * from stores where address = :address")
    suspend fun FindByAddress(address: String): Store?

    @Query(
        "select * from stores " +
            "where latitude between :minLatitude and :maxLatitude " +
            "and longitude between :minLongitude and :maxLongitude"
    )
    suspend fun FindAllWithinRange(
        minLatitude: Double, maxLatitude: Double,
        minLongitude: Double, maxLongitude: Double,
    ): List<Store>
}
