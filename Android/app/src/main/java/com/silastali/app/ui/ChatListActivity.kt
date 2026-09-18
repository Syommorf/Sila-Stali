package com.silastali.app.ui

import android.content.Intent
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.SilastaliApp
import com.silastali.app.data.ChatItem
import com.silastali.app.databinding.ActivityChatListBinding
import com.silastali.app.ui.adapters.ChatAdapter
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ChatListActivity : AppCompatActivity() {
    private lateinit var binding: ActivityChatListBinding
    private val app by lazy { application as SilastaliApp }
    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }
    private val handler = Handler(Looper.getMainLooper())
    private var chats = emptyList<ChatItem>()

    private val pollTask = object : Runnable {
        override fun run() {
            if (isFinishing || isDestroyed) return
            loadChats(silent = true)
            handler.postDelayed(this, 10_000L)
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityChatListBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Чат"
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.rvChats.layoutManager = LinearLayoutManager(this)

        binding.fabNewChat.setOnClickListener {
            startActivity(Intent(this, NewChatActivity::class.java))
        }

        loadChats(silent = false)
    }

    override fun onResume() {
        super.onResume()
        app.apiClient.token = prefs.getString("token", null)
        getSharedPreferences("app_state", MODE_PRIVATE).edit().putBoolean("app_visible", true).apply()
        loadChats(silent = true)
        if (!handler.hasCallbacks(pollTask)) {
            handler.postDelayed(pollTask, 10_000L)
        }
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacks(pollTask)
        getSharedPreferences("app_state", MODE_PRIVATE).edit().putBoolean("app_visible", false).apply()
    }

    private fun loadChats(silent: Boolean) {
        if (!silent) binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val list = app.apiClient.getChats()
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    chats = list
                    binding.tvEmpty.visibility = if (list.isEmpty()) View.VISIBLE else View.GONE
                    binding.rvChats.adapter = ChatAdapter(list) { chat -> openChat(chat) }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    if (!silent) {
                        Toast.makeText(this@ChatListActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                    }
                }
            }
        }
    }

    private fun openChat(chat: ChatItem) {
        startActivity(Intent(this, ChatRoomActivity::class.java).apply {
            putExtra("chat_id", chat.id)
            putExtra("chat_title", ChatAdapter.title(chat))
            putExtra("chat_type", chat.type)
        })
    }
}