package com.silastali.app.ui

import android.app.AlertDialog
import android.app.NotificationManager
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.silastali.app.SilastaliApp
import com.silastali.app.data.CrewInvite
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class InvitePrompter(private val activity: AppCompatActivity) {
    companion object {
        private const val POLL_INTERVAL_MS = 10_000L
        private const val PREFS = "invites"
        private const val KEY_HANDLED = "handled"
        private const val NOTIFY_BASE = 1001
    }

    private val app by lazy { activity.application as SilastaliApp }
    private val authPrefs by lazy { activity.getSharedPreferences("auth", Context.MODE_PRIVATE) }
    private val invitePrefs by lazy { activity.getSharedPreferences(PREFS, Context.MODE_PRIVATE) }
    private val handler = Handler(Looper.getMainLooper())
    private var dialogOpen = false

    private val pollTask = object : Runnable {
        override fun run() {
            checkInvites()
            handler.postDelayed(this, POLL_INTERVAL_MS)
        }
    }

    fun start() {
        if (authPrefs.getString("role", "") !in listOf("apprentice", "bender", "senior_bender")) return
        if (dialogOpen) return
        setForegroundFlag(true)
        handler.removeCallbacks(pollTask)
        handler.post(pollTask)
    }

    fun stop() {
        handler.removeCallbacks(pollTask)
        setForegroundFlag(false)
    }

    private fun setForegroundFlag(value: Boolean) {
        activity.getSharedPreferences("app_state", Context.MODE_PRIVATE).edit().putBoolean("app_visible", value).apply()
    }

    private fun isWorker(): Boolean =
        authPrefs.getString("role", "") in listOf("apprentice", "bender", "senior_bender")

    private fun shownInviteIds(): Set<Int> =
        invitePrefs.getStringSet(KEY_HANDLED, emptySet())?.mapNotNull { it.toIntOrNull() }?.toSet() ?: emptySet()

    private fun markShown(id: Int) {
        val current = invitePrefs.getStringSet(KEY_HANDLED, emptySet())?.toMutableSet() ?: mutableSetOf()
        current.add(id.toString())
        invitePrefs.edit().putStringSet(KEY_HANDLED, current).apply()
    }

    private fun checkInvites() {
        if (!isWorker() || dialogOpen) return
        val token = authPrefs.getString("token", null)
        if (token.isNullOrEmpty()) return
        CoroutineScope(Dispatchers.IO).launch {
            try {
                app.apiClient.token = token
                val invites = app.apiClient.getCrewInvites()
                val handled = shownInviteIds()
                val fresh = invites.firstOrNull { it.id !in handled } ?: return@launch
                withContext(Dispatchers.Main) {
                    if (activity.isFinishing || activity.isDestroyed || dialogOpen) return@withContext
                    showDialog(fresh)
                }
            } catch (_: Exception) {
            }
        }
    }

    private fun showDialog(invite: CrewInvite) {
        dialogOpen = true
        markShown(invite.id)
        AlertDialog.Builder(activity)
            .setTitle("Приглашение в бригаду")
            .setMessage(
                "${invite.inviter_name} приглашает вас в бригаду.\n\n" +
                    "Заказ №${invite.order_number}\n" +
                    "Деталь: ${invite.part_number} (${invite.quantity} шт.)\n\n" +
                    "Подтвердить участие?"
            )
            .setPositiveButton("Принять") { _, _ ->
                dialogOpen = false
                respond(invite.id, true)
            }
            .setNegativeButton("Отклонить") { _, _ ->
                dialogOpen = false
                respond(invite.id, false)
            }
            .setNeutralButton("Позже", null)
            .setOnDismissListener { dialogOpen = false }
            .setCancelable(true)
            .show()
    }

    private fun respond(inviteId: Int, accept: Boolean) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val token = authPrefs.getString("token", null)
                if (!token.isNullOrEmpty()) {
                    app.apiClient.token = token
                    app.apiClient.respondCrewInvite(inviteId, accept)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(activity, "Не удалось отправить ответ: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            } finally {
                val nm = activity.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                nm.cancel(NOTIFY_BASE + (inviteId % 50000))
                withContext(Dispatchers.Main) {
                    Toast.makeText(
                        activity,
                        if (accept) "Вы приняты в бригаду" else "Приглашение отклонено",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }
        }
    }
}