package com.silastali.app.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.os.Handler
import android.os.Looper
import com.silastali.app.SilastaliApp
import com.silastali.app.data.CrewInvite
import com.silastali.app.ui.OrderDetailActivity

class InvitePollService : Service() {

    companion object {
        const val ACTION_RESPOND = "com.silastali.app.action.RESPOND_INVITE"
        const val EXTRA_INVITE_ID = "invite_id"
        const val EXTRA_ACCEPT = "accept"
        private const val CHANNEL_ID = "crew_invites"
        private const val NOTIFY_ID = 1001
        private const val POLL_INTERVAL_MS = 10_000L

        fun intent(context: Context): Intent = Intent(context, InvitePollService::class.java)
    }

    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }
    private val handler = Handler(Looper.getMainLooper())
    private val notifiedInvites = mutableSetOf<Int>()

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
        when (intent?.action) {
            ACTION_RESPOND -> handleRespond(intent)
            else -> {
                if (!handler.hasCallbacks(pollTask)) {
                    handler.post(pollTask)
                }
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        handler.removeCallbacks(pollTask)
        super.onDestroy()
    }

    private fun createChannel() {
        if (android.os.Build.VERSION.SDK_INT >= 26) {
            val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Приглашения в бригаду",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Уведомления о приглашениях в бригаду"
            }
            manager.createNotificationChannel(channel)
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
                val invites = api.getCrewInvites()
                val fresh = invites.filter { it.id !in notifiedInvites }
                val appVisible = getSharedPreferences("app_state", Context.MODE_PRIVATE)
                    .getBoolean("app_visible", false)
                if (fresh.isNotEmpty() && !appVisible) {
                    val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                    fresh.forEach { invite ->
                        manager.notify(NOTIFY_ID + (invite.id % 50000), buildInviteNotification(invite))
                        notifiedInvites.add(invite.id)
                    }
                } else if (fresh.isNotEmpty()) {
                    // приложение открыто — уведомление покажет экранный диалог (InvitePrompter)
                    fresh.forEach { notifiedInvites.add(it.id) }
                }
            } catch (e: Exception) {
            } finally {
                handler.postDelayed(pollTask, POLL_INTERVAL_MS)
            }
        }.start()
    }

    private fun buildInviteNotification(invite: CrewInvite): Notification {
        val contentIntent = PendingIntent.getActivity(
            this,
            invite.id,
            Intent(this, OrderDetailActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
                putExtra("order_id", invite.order_id)
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        fun respondPending(accept: Boolean): PendingIntent {
            val intent = Intent(this, InvitePollService::class.java).apply {
                action = ACTION_RESPOND
                putExtra(EXTRA_INVITE_ID, invite.id)
                putExtra(EXTRA_ACCEPT, accept)
            }
            return PendingIntent.getService(
                this,
                1000 + invite.id + (if (accept) 0 else 50000),
                intent,
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            )
        }

        val builder = if (android.os.Build.VERSION.SDK_INT >= 26) {
            Notification.Builder(this, CHANNEL_ID)
        } else {
            @Suppress("DEPRECATION")
            Notification.Builder(this)
        }
        return builder
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle("Приглашение в бригаду")
            .setContentText("${invite.inviter_name} приглашает вас в бригаду: №${invite.order_number}, деталь ${invite.part_number}")
            .setStyle(Notification.BigTextStyle().bigText(
                "${invite.inviter_name} приглашает вас в бригаду.\nЗаказ №${invite.order_number}, деталь ${invite.part_number} (${invite.quantity} шт.)"
            ))
            .setAutoCancel(true)
            .setContentIntent(contentIntent)
            .addAction(0, "Отклонить", respondPending(false))
            .addAction(0, "Принять", respondPending(true))
            .build()
    }

    private fun handleRespond(intent: Intent) {
        val inviteId = intent.getIntExtra(EXTRA_INVITE_ID, -1)
        val accept = intent.getBooleanExtra(EXTRA_ACCEPT, false)
        if (inviteId <= 0) return
        Thread {
            try {
                val token = prefs.getString("token", null)
                if (!token.isNullOrEmpty()) {
                    val api = (application as SilastaliApp).apiClient
                    api.token = token
                    api.respondCrewInvite(inviteId, accept)
                }
            } catch (e: Exception) {
            } finally {
                notifiedInvites.add(inviteId)
                val manager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
                manager.cancel(NOTIFY_ID + (inviteId % 50000))
                handler.post { stopIfNoToken() }
            }
        }.start()
    }

    private fun stopIfNoToken() {
        if (prefs.getString("token", null).isNullOrEmpty()) {
            stopSelf()
        }
    }
}