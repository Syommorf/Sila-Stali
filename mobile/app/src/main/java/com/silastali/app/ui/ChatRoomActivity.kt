package com.silastali.app.ui

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.R
import com.silastali.app.SilastaliApp
import com.silastali.app.data.ChatMessage
import com.silastali.app.data.UserItem
import com.silastali.app.databinding.ActivityChatRoomBinding
import com.silastali.app.ui.adapters.ChatMessageAdapter
import com.silastali.app.ui.adapters.MemberPickerAdapter
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class ChatRoomActivity : AppCompatActivity() {
    private lateinit var binding: ActivityChatRoomBinding
    private val app by lazy { application as SilastaliApp }
    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }
    private val handler = Handler(Looper.getMainLooper())

    private var chatId = 0
    private var chatType = "channel"
    private var myUserId = 0
    private var lastMessageId = 0
    private var messages = mutableListOf<ChatMessage>()
    private var adapter = ChatMessageAdapter(messages, 0, true)

    private val pollTask = object : Runnable {
        override fun run() {
            if (isFinishing || isDestroyed) return
            pollNew()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityChatRoomBinding.inflate(layoutInflater)
        setContentView(binding.root)

        chatId = intent.getIntExtra("chat_id", 0)
        chatType = intent.getStringExtra("chat_type") ?: "channel"
        myUserId = prefs.getInt("user_id", 0)
        val title = intent.getStringExtra("chat_title") ?: "Чат"

        setSupportActionBar(binding.toolbar)
        supportActionBar?.title = title
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        if (chatType == "group") {
            binding.toolbar.inflateMenu(R.menu.menu_chat_room)
            binding.toolbar.setOnMenuItemClickListener { item ->
                if (item.itemId == R.id.action_add_member) {
                    showAddMembers()
                    true
                } else false
            }
        }

        binding.rvMessages.layoutManager = LinearLayoutManager(this)
        binding.rvMessages.adapter = adapter

        binding.btnSend.setOnClickListener { sendMessage() }

        loadHistory()
    }

    override fun onResume() {
        super.onResume()
        app.apiClient.token = prefs.getString("token", null)
        getSharedPreferences("app_state", MODE_PRIVATE).edit().putBoolean("app_visible", true).apply()
        if (!handler.hasCallbacks(pollTask)) {
            handler.postDelayed(pollTask, 5_000L)
        }
    }

    override fun onPause() {
        super.onPause()
        handler.removeCallbacks(pollTask)
        getSharedPreferences("app_state", MODE_PRIVATE).edit().putBoolean("app_visible", false).apply()
    }

    private fun loadHistory() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val resp = app.apiClient.getChatMessages(chatId, afterId = 0, limit = 200)
                withContext(Dispatchers.Main) {
                    messages.clear()
                    messages.addAll(resp.messages)
                    lastMessageId = messages.lastOrNull()?.id ?: 0
                    refresh()
                    markRead()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ChatRoomActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun pollNew() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val resp = app.apiClient.getChatMessages(chatId, afterId = lastMessageId, limit = 200)
                val fresh = resp.messages
                withContext(Dispatchers.Main) {
                    if (fresh.isNotEmpty()) {
                        val wasAtBottom = isAtBottom()
                        messages.addAll(fresh)
                        lastMessageId = messages.lastOrNull()?.id ?: lastMessageId
                        refresh()
                        if (wasAtBottom) scrollToBottom()
                        markRead()
                    }
                }
            } catch (e: Exception) {
            } finally {
                handler.postDelayed(pollTask, 5_000L)
            }
        }
    }

    private fun sendMessage() {
        val text = binding.etInput.text.toString().trim()
        if (text.isEmpty()) return
        binding.etInput.setText("")
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val msg = app.apiClient.sendChatMessage(chatId, text)
                withContext(Dispatchers.Main) {
                    messages.add(msg)
                    lastMessageId = msg.id
                    refresh()
                    scrollToBottom()
                    markRead()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.etInput.setText(text)
                    Toast.makeText(this@ChatRoomActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun markRead() {
        if (lastMessageId > 0) {
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    app.apiClient.markChatRead(chatId, lastMessageId)
                } catch (e: Exception) {
                }
            }
        }
    }

    private fun refresh() {
        val showSenders = chatType != "dm"
        adapter = ChatMessageAdapter(messages.toList(), myUserId, showSenders)
        binding.rvMessages.adapter = adapter
        adapter.notifyDataSetChanged()
    }

    private fun scrollToBottom() {
        if (messages.isNotEmpty()) {
            binding.rvMessages.scrollToPosition(messages.size - 1)
        }
    }

    private fun isAtBottom(): Boolean {
        val lm = binding.rvMessages.layoutManager as LinearLayoutManager
        val lastVisible = lm.findLastVisibleItemPosition()
        return messages.isEmpty() || lastVisible >= messages.size - 2
    }

    private fun showAddMembers() {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val users = app.apiClient.getUsers()
                    .filter { it.id != myUserId && it.role != com.silastali.app.ui.RoleNames.ADMIN }
                withContext(Dispatchers.Main) {
                    val pickerAdapter = MemberPickerAdapter(users, single = false)
                    val rv = android.widget.TextView(this@ChatRoomActivity).apply {
                        text = "Выберите участников:"
                        textSize = 14f
                        setTextColor(0xFFA9B7C6.toInt())
                        setPadding(48, 24, 48, 8)
                    }
                    val recycler = androidx.recyclerview.widget.RecyclerView(this@ChatRoomActivity).apply {
                        layoutManager = androidx.recyclerview.widget.LinearLayoutManager(this@ChatRoomActivity)
                        adapter = pickerAdapter
                    }
                    val container = android.widget.LinearLayout(this@ChatRoomActivity).apply {
                        orientation = android.widget.LinearLayout.VERTICAL
                        setPadding(8, 0, 8, 8)
                        addView(rv)
                        addView(recycler, android.widget.LinearLayout.LayoutParams(
                            android.view.ViewGroup.LayoutParams.MATCH_PARENT,
                            520
                        ))
                    }
                    androidx.appcompat.app.AlertDialog.Builder(this@ChatRoomActivity)
                        .setTitle("Добавить участников")
                        .setView(container)
                        .setPositiveButton("Добавить") { _, _ ->
                            val ids = pickerAdapter.selectedIds()
                            if (ids.isNotEmpty()) addMembers(ids)
                        }
                        .setNegativeButton("Отмена", null)
                        .show()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ChatRoomActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun addMembers(ids: List<Int>) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                app.apiClient.addChatMembers(chatId, ids)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ChatRoomActivity, "Участники добавлены", Toast.LENGTH_SHORT).show()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@ChatRoomActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }
}