package com.silastali.app.ui

import android.content.Intent
import android.os.Bundle
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.silastali.app.databinding.ActivityManagerBinding

class ManagerActivity : AppCompatActivity() {
    private lateinit var binding: ActivityManagerBinding
    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityManagerBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val fullName = prefs.getString("full_name", "") ?: ""
        binding.tvManagerName.text = fullName

        binding.btnWork.setOnClickListener {
            startActivity(Intent(this, WorkMenuActivity::class.java))
        }

        binding.btnStaff.setOnClickListener {
            startActivity(Intent(this, StaffMenuActivity::class.java))
        }

        binding.btnChat.setOnClickListener {
            startActivity(Intent(this, ChatListActivity::class.java))
        }

        binding.btnLogout.setOnClickListener { showLogoutDialog() }

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
        prefs.edit().clear().apply()
        startActivity(Intent(this, LoginActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        })
        finish()
    }

    override fun onResume() {
        super.onResume()
        app.apiClient.token = prefs.getString("token", null)
        getSharedPreferences("app_state", MODE_PRIVATE).edit().putBoolean("app_visible", true).apply()
    }

    override fun onPause() {
        super.onPause()
        getSharedPreferences("app_state", MODE_PRIVATE).edit().putBoolean("app_visible", false).apply()
    }

    private val app get() = application as com.silastali.app.SilastaliApp
}