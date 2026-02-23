package com.example.grocerystoreorganizer.data.local.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import com.example.grocerystoreorganizer.data.local.entity.Sale

@Dao
interface SaleDao {
    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertItems(vararg items: Sale): List<Long>

    @Update
    suspend fun updateItems(vararg items: Sale): Int

    @Query("select * from sales where rowid = :id")
    suspend fun FindById(id: Int): Sale?
}
