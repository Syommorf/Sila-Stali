package com.silastali.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import com.silastali.app.SilastaliApp
import com.silastali.app.ui.ChatListActivity

class ChatUnreadService : Service() {

    companion object {
        private const val CHANNEL_ID = "chat"
        private const val NOTIFY_ID = 2001
        private const val POLL_INTERVAL_MS = 10_000L
        private const val PREFS_APP_STATE = "app_state"
        private const val PREFS_BASELINE = "chat_unread_baseline"

        fun intent(context: Context): Intent = Intent(context, ChatUnreadService::class.java)
    }

    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }
    private val appState by lazy { getSharedPreferences(PREFS_APP_STATE, Context.MODE_PRIVATE) }
    private val handler = Handler(Looper.getMainLooper())

    private val pollTask = object : Runnable {
        override fun run() {
            pollOnce()
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!handler.hasCallbacks(pollTask)) {
            handler.post(pollTask)
        }
        return START_STICKY
    }

    override fun onDestroy() {
        handler.removeCallbacks(pollTask)
        super.onDestroy()
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            manager.createNotificationChannel(
                NotificationChannel(CHANNEL_ID, "Сообщения чата", NotificationManager.IMPORTANCE_HIGH).apply {
                    description = "Уведомления о новых сообщениях в чате"
                }
            )
        }
    }

    private fun pollOnce() {
        val token = prefs.getString("token", null)
        if (token.isNullOrEmpty()) {
            stopSelf()
            return
        }
        Thread {
            try {
                val api = (application as SilastaliApp).apiClient
                api.token = token
                val chats = api.getChats()
                val total = chats.sumOf { it.unread_count }
                val appVisible = appState.getBoolean("app_visible", false)
                var baseline = appState.getInt(PREFS_BASELINE, 0)

                if (appVisible) {
                    // приложение на экране — уведомление не нужно, но двигаем базовую линию
                    if (total != baseline) {
                        appState.edit().putInt(PREFS_BASELINE, total).apply()
                    }
                } else {
                    if (total > baseline) {
                        baseline = total
                        appState.edit().putInt(PREFS_BASELINE, total).apply()
                        if (canNotify()) {
                            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                            manager.notify(NOTIFY_ID, buildNotification(total))
                        }
                    } else if (total == 0 && baseline != 0) {
                        appState.edit().putInt(PREFS_BASELINE, 0).apply()
                    }
                }
            } catch (e: Exception) {
            } finally {
                handler.postDelayed(pollTask, POLL_INTERVAL_MS)
            }
        }.start()
    }

    private fun canNotify(): Boolean {
        return Build.VERSION.SDK_INT < 33 ||
            checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED
    }

    private fun buildNotification(unread: Int): Notification {
        val contentIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, ChatListActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        val builder = if (Build.VERSION.SDK_INT >= 26) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        val text = if (unread == 1) "У вас 1 непрочитанное сообщение"
        else "У вас $unread непрочитанных сообщений"
        return builder
            .setSmallIcon(android.R.drawable.ic_dialog_email)
            .setContentTitle("Сила Стали: чат")
            .setContentText(text)
            .setStyle(Notification.BigTextStyle().bigText(text))
            .setAutoCancel(true)
            .setContentIntent(contentIntent)
            .build()
    }
}