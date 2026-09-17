package com.silastali.app.data

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import com.silastali.app.data.db.AppDatabase
import com.silastali.app.data.network.ApiClient
import kotlinx.coroutines.*

class SyncManager(
    private val context: Context,
    private val database: AppDatabase,
    private val apiClient: ApiClient
) {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    fun isOnline(): Boolean {
        val cm = context.getSystemService(Context.CONNECTIVITY_SERVICE) as ConnectivityManager
        val network = cm.activeNetwork ?: return false
        val caps = cm.getNetworkCapabilities(network) ?: return false
        return caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)
    }

    fun syncPending() {
        scope.launch {
            try {
                val pending = database.workDao().getUnsynced()
                if (pending.isEmpty()) return@launch
                val requests = pending.map {
                    WorkCreateRequest(
                        part_number = it.part_number,
                        quantity = it.quantity,
                        note = it.note,
                        start_time = it.start_time,
                        end_time = it.end_time
                    )
                }
                apiClient.syncWorks(requests)
                pending.forEach { database.workDao().markSynced(it.id) }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
