package com.silastali.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.SilastaliApp
import com.silastali.app.data.UserItem
import com.silastali.app.databinding.ActivityNewChatBinding
import com.silastali.app.ui.adapters.MemberPickerAdapter
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class NewChatActivity : AppCompatActivity() {
    private lateinit var binding: ActivityNewChatBinding
    private val app by lazy { application as SilastaliApp }
    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }
    private val myUserId by lazy { prefs.getInt("user_id", 0) }
    private var users = emptyList<UserItem>()
    private var pickerAdapter: MemberPickerAdapter? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityNewChatBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Новый чат"
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.rgType.setOnCheckedChangeListener { _, checkedId ->
            val isGroup = checkedId == binding.rbGroup.id
            binding.etChatName.visibility = if (isGroup) View.VISIBLE else View.GONE
            binding.tvHint.text = if (isGroup) "Выберите участников:" else "Выберите сотрудника:"
            rebuildPicker(single = !isGroup)
        }

        binding.btnCreate.setOnClickListener { create() }

        loadUsers()
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

    private fun loadUsers() {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val list = app.apiClient.getUsers()
                    .filter { it.id != myUserId }
                    .sortedBy { it.full_name }
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    users = list
                    rebuildPicker(single = true)
                    if (list.isEmpty()) {
                        binding.tvHint.text = "Некому писать — сотрудников нет"
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@NewChatActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun rebuildPicker(single: Boolean) {
        pickerAdapter = MemberPickerAdapter(users, single = single)
        binding.rvMembers.layoutManager = LinearLayoutManager(this)
        binding.rvMembers.adapter = pickerAdapter
    }

    private fun create() {
        val isGroup = binding.rbGroup.isChecked
        pickerAdapter ?: return
        val selected = pickerAdapter!!.selectedIds()

        if (isGroup) {
            val name = binding.etChatName.text.toString().trim()
            if (name.isEmpty()) {
                Toast.makeText(this, "Введите название группы", Toast.LENGTH_SHORT).show()
                return
            }
            if (selected.isEmpty()) {
                Toast.makeText(this, "Выберите хотя бы одного участника", Toast.LENGTH_SHORT).show()
                return
            }
            createChat(name, selected)
        } else {
            if (selected.isEmpty()) {
                Toast.makeText(this, "Выберите сотрудника", Toast.LENGTH_SHORT).show()
                return
            }
            createDm(selected.first())
        }
    }

    private fun createDm(userId: Int) {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val chat = app.apiClient.createDm(userId)
                withContext(Dispatchers.Main) {
                    openRoom(chat.id, chat.other_user_name ?: "Чат", "dm")
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@NewChatActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun createChat(name: String, memberIds: List<Int>) {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val chat = app.apiClient.createChat(name, memberIds)
                withContext(Dispatchers.Main) {
                    openRoom(chat.id, chat.name ?: name, "group")
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@NewChatActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun openRoom(chatId: Int, title: String, type: String) {
        val intent = Intent(this, ChatRoomActivity::class.java).apply {
            putExtra("chat_id", chatId)
            putExtra("chat_title", title)
            putExtra("chat_type", type)
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        startActivity(intent)
        finish()
    }
}