package com.silastali.app.data.db

import androidx.room.*

@Entity(tableName = "pending_works")
data class PendingWork(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val part_number: String,
    val quantity: Int,
    val note: String,
    val start_time: String,
    val end_time: String? = null,
    val synced: Boolean = false
)

@Dao
interface WorkDao {
    @Query("SELECT * FROM pending_works WHERE synced = 0 ORDER BY id ASC")
    suspend fun getUnsynced(): List<PendingWork>

    @Insert
    suspend fun insert(work: PendingWork): Long

    @Query("UPDATE pending_works SET synced = 1 WHERE id = :id")
    suspend fun markSynced(id: Long)

    @Query("DELETE FROM pending_works WHERE synced = 1")
    suspend fun deleteSynced()
}
