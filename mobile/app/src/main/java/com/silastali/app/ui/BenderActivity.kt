package com.silastali.app.ui

import android.content.Intent
import android.os.Bundle
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.silastali.app.SilastaliApp
import com.silastali.app.data.SyncManager
import com.silastali.app.databinding.ActivityBenderBinding

class BenderActivity : AppCompatActivity() {
    private lateinit var binding: ActivityBenderBinding
    private val app by lazy { application as SilastaliApp }
    private val syncManager by lazy { SyncManager(this, app.database, app.apiClient) }

    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBenderBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val fullName = prefs.getString("full_name", "") ?: ""
        binding.tvWorkerName.text = fullName
        binding.tvWorkerRole.text = RoleNames.displayName(prefs.getString("role", "bender") ?: "bender")

        binding.btnAddDetail.setOnClickListener {
            val intent = Intent(this, DetailEntryActivity::class.java)
            startActivity(intent)
        }

        binding.btnMyStats.setOnClickListener {
            startActivity(Intent(this, MyStatsActivity::class.java))
        }

        binding.btnLogout.setOnClickListener { showLogoutDialog() }

        binding.btnOrders.setOnClickListener {
            startActivity(Intent(this, OrderListActivity::class.java))
        }

        binding.btnChat.setOnClickListener {
            startActivity(Intent(this, ChatListActivity::class.java))
        }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                showLogoutDialog()
            }
        })
    }

    private fun showLogoutDialog() {
        AlertDialog.Builder(this)
            .setTitle("Выход")
            .setMessage("Выйти из приложения?")
            .setPositiveButton("Да") { _, _ -> logout() }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun logout() {
        getSharedPreferences("auth", MODE_PRIVATE).edit().clear().apply()
        startActivity(Intent(this, LoginActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        })
        finish()
    }

    override fun onResume() {
        super.onResume()
        app.apiClient.token = prefs.getString("token", null)
        syncManager.syncPending()
        invitePrompter.start()
    }

    override fun onPause() {
        super.onPause()
        invitePrompter.stop()
    }

    private val invitePrompter by lazy { InvitePrompter(this) }
}
