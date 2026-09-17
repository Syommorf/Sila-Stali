package com.silastali.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.data.UserCreateRequest
import com.silastali.app.data.UserItem
import com.silastali.app.data.UserUpdateRequest
import com.silastali.app.databinding.ActivityAdminBinding
import com.silastali.app.ui.adapters.UserAdapter
import com.silastali.app.SilastaliApp
import kotlinx.coroutines.*

class AdminActivity : AppCompatActivity() {
    private lateinit var binding: ActivityAdminBinding
    private val app by lazy { application as SilastaliApp }
    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAdminBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Администратор"
        binding.toolbar.setNavigationOnClickListener { showLogoutDialog() }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                showLogoutDialog()
            }
        })

        val fullName = prefs.getString("full_name", "") ?: ""
        binding.tvAdminName.text = fullName

        binding.rvManagers.layoutManager = LinearLayoutManager(this)

        binding.fabAddManager.setOnClickListener { showAddUserDialog() }

        binding.btnLogout.setOnClickListener { showLogoutDialog() }

        binding.btnOrders.setOnClickListener {
            startActivity(Intent(this, OrderListActivity::class.java))
        }

        binding.btnChat.setOnClickListener {
            startActivity(Intent(this, ChatListActivity::class.java))
        }

        loadUsers()
    }

    private fun loadUsers() {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val users = app.apiClient.getUsers()
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.tvEmpty.visibility = if (users.isEmpty()) View.VISIBLE else View.GONE
                    binding.rvManagers.visibility = if (users.isEmpty()) View.GONE else View.VISIBLE
                    binding.rvManagers.adapter = UserAdapter(
                        users,
                        { user -> showEditUserDialog(user) },
                        { user -> confirmDelete(user) },
                        canDelete = { user -> true },
                        showPassword = true,
                        groupByBlock = true
                    )
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@AdminActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun label(text: String) = TextView(this).apply {
        this.text = text
        textSize = 13f
        setPadding(48, 24, 48, 0)
        setTextColor(0xFF666666.toInt())
    }

    private fun showAddUserDialog() {
        val inputs = arrayOf("Логин:", "Пароль:", "ФИО:").map { field ->
            EditText(this).apply {
                hint = field
                setPadding(48, 32, 48, 32)
            }
        }
        val picker = BlockRolePicker(this, RoleNames.allBlocks, RoleNames.BLOCK_BENDER, null)

        val container = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(64, 32, 64, 16)
            inputs.forEach { addView(it) }
            addView(label("Блок"))
            addView(picker.blockRadio)
            addView(label("Должность"))
            addView(picker.roleRadio)
        }

        AlertDialog.Builder(this)
            .setTitle("Новый сотрудник")
            .setView(container)
            .setPositiveButton("Создать") { _, _ ->
                val username = inputs[0].text.toString().trim()
                val password = inputs[1].text.toString().trim()
                val fullName = inputs[2].text.toString().trim()
                if (username.isEmpty() || password.isEmpty() || fullName.isEmpty()) {
                    Toast.makeText(this, "Заполните все поля", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                createUser(username, password, fullName, picker.selectedRole(), picker.selectedBlock())
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun createUser(username: String, password: String, fullName: String, role: String, block: String) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                app.apiClient.createUser(UserCreateRequest(username, password, fullName, role, block))
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@AdminActivity, "Сотрудник создан", Toast.LENGTH_SHORT).show()
                    loadUsers()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@AdminActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun showEditUserDialog(user: UserItem) {
        val etUsername = EditText(this).apply {
            hint = "Логин"
            setText(user.username)
            setPadding(48, 32, 48, 32)
        }
        val etPassword = EditText(this).apply {
            hint = "Пароль"
            setText(user.password_plain ?: "")
            setPadding(48, 32, 48, 32)
        }
        val etFullName = EditText(this).apply {
            hint = "ФИО"
            setText(user.full_name)
            setPadding(48, 32, 48, 32)
        }
        val initialBlock = if (user.role == RoleNames.MANAGER) RoleNames.BLOCK_CHIEF
        else if (RoleNames.allBlocks.firstOrNull { it.first == user.block } != null) user.block
        else RoleNames.BLOCK_BENDER
        val picker = BlockRolePicker(this, RoleNames.allBlocks, initialBlock, user.role)

        val container = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(64, 32, 64, 16)
            addView(etUsername)
            addView(etPassword)
            addView(etFullName)
            addView(label("Блок"))
            addView(picker.blockRadio)
            addView(label("Должность"))
            addView(picker.roleRadio)
        }

        AlertDialog.Builder(this)
            .setTitle("Данные: ${user.full_name}")
            .setView(container)
            .setPositiveButton("Сохранить") { _, _ ->
                val username = etUsername.text.toString().trim()
                val password = etPassword.text.toString()
                val fullName = etFullName.text.toString().trim()
                if (username.isEmpty() || fullName.isEmpty()) {
                    Toast.makeText(this, "Логин и ФИО не могут быть пустыми", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                saveUserCredentials(user, username, password, fullName, picker.selectedRole(), picker.selectedBlock())
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun saveUserCredentials(
        user: UserItem,
        username: String,
        password: String,
        fullName: String,
        role: String,
        block: String,
    ) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                app.apiClient.updateUser(
                    user.id,
                    UserUpdateRequest(
                        full_name = fullName,
                        username = username,
                        password = password.ifEmpty { null },
                        role = role,
                        block = block
                    )
                )
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@AdminActivity, "Сохранено", Toast.LENGTH_SHORT).show()
                    loadUsers()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@AdminActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun confirmDelete(user: UserItem) {
        AlertDialog.Builder(this)
            .setTitle("Удалить сотрудника?")
            .setMessage("Удалить ${user.full_name}?")
            .setPositiveButton("Удалить") { _, _ ->
                CoroutineScope(Dispatchers.IO).launch {
                    try {
                        app.apiClient.deleteUser(user.id)
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@AdminActivity, "Удалён", Toast.LENGTH_SHORT).show()
                            loadUsers()
                        }
                    } catch (e: Exception) {
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@AdminActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }
            .setNegativeButton("Отмена", null)
            .show()
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
}