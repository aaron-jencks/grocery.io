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
    fun insertItems(vararg items: Sale)

    @Update
    fun updateItems(vararg items: Sale)

    @Query("select * from sales where rowid = :id")
    fun FindById(id: Int): Sale?
}