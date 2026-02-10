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
    fun insertItems(vararg items: Store)

    @Update
    fun updateItems(vararg items: Store)

    @Query("select * from stores where rowid = :id")
    fun FindById(id: Int): Store?

    @Query("select * from stores where address = :address")
    fun FindByAddress(address: String): Store?

    @Query("select * from stores where :minLatitude <= latitude <= :maxLatitude and :minLongitude <= longitude <= :maxLongitude")
    fun FindAllWithinRange(
        minLatitude: Double, maxLatitude: Double,
        minLongitude: Double, maxLongitude: Double,
    ): List<Store>
}