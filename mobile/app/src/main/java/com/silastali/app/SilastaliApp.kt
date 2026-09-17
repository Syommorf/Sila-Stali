package com.silastali.app

import android.app.Application
import android.content.Intent
import com.silastali.app.data.db.AppDatabase
import com.silastali.app.data.network.ApiClient
import com.silastali.app.service.ChatUnreadService
import com.silastali.app.service.InvitePollService

class SilastaliApp : Application() {
    val database by lazy { AppDatabase.getInstance(this) }
    val apiClient by lazy { ApiClient(this) }

    override fun onCreate() {
        super.onCreate()
        Thread.setDefaultUncaughtExceptionHandler(CrashHandler(this))
        startInvitePollingIfLoggedIn()
        startChatPollingIfLoggedIn()
    }

    private fun startInvitePollingIfLoggedIn() {
        val prefs = getSharedPreferences("auth", MODE_PRIVATE)
        val token = prefs.getString("token", null)
        val role = prefs.getString("role", "bender") ?: "bender"
        if (token.isNullOrEmpty()) return
        if (role !in listOf("apprentice", "bender", "senior_bender")) return
        try {
            startService(Intent(this, InvitePollService::class.java))
        } catch (e: Exception) {
        }
    }

    private fun startChatPollingIfLoggedIn() {
        val prefs = getSharedPreferences("auth", MODE_PRIVATE)
        val token = prefs.getString("token", null)
        if (token.isNullOrEmpty()) return
        try {
            startService(Intent(this, ChatUnreadService::class.java))
        } catch (e: Exception) {
        }
    }
}
