package com.silastali.app.ui

import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.RadioButton
import android.widget.RadioGroup
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.SilastaliApp
import com.silastali.app.data.UserCreateRequest
import com.silastali.app.data.UserItem
import com.silastali.app.data.UserUpdateRequest
import com.silastali.app.databinding.ActivityUsersBinding
import com.silastali.app.ui.adapters.UserAdapter
import kotlinx.coroutines.*

class UsersActivity : AppCompatActivity() {
    private lateinit var binding: ActivityUsersBinding
    private val app by lazy { application as SilastaliApp }
    private val blockFilter by lazy { intent.getStringExtra("block") }
    private val isFiltered get() = blockFilter != null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityUsersBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = blockFilter?.let { RoleNames.blockDisplayName(it) } ?: "Сотрудники"
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.rvUsers.layoutManager = LinearLayoutManager(this)

        binding.fabAddUser.setOnClickListener { showAddUserDialog() }

        loadUsers()
    }

    private fun loadUsers() {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val users = app.apiClient.getUsers()
                    .filter { user -> blockFilter == null || user.block == blockFilter }
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.rvUsers.adapter = UserAdapter(users, { user -> showEditDialog(user) }, { user -> deleteUser(user) }, showPassword = true, groupByBlock = !isFiltered)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@UsersActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
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
        val picker = BlockRolePicker(this, RoleNames.workerBlocks, blockFilter ?: RoleNames.BLOCK_BENDER, null)

        val container = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(64, 32, 64, 16)
            inputs.forEach { addView(it) }
            if (!isFiltered) {
                addView(label("Блок (участок)"))
                addView(picker.blockRadio)
            }
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
                    Toast.makeText(this@UsersActivity, "Сотрудник создан", Toast.LENGTH_SHORT).show()
                    loadUsers()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@UsersActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun showEditDialog(user: UserItem) {
        val passwordInput = EditText(this).apply {
            hint = if (!user.password_plain.isNullOrEmpty()) "Пароль: ${user.password_plain}" else "Новый пароль"
            setText(user.password_plain.orEmpty().trim())
            setPadding(48, 32, 48, 32)
        }
        val initialBlock = blockFilter ?: RoleNames.workerBlocks.firstOrNull { it.first == user.block }?.first
            ?: if (user.role == RoleNames.MANAGER) RoleNames.BLOCK_BENDER else RoleNames.BLOCK_BENDER
        val picker = BlockRolePicker(this, RoleNames.workerBlocks, initialBlock, user.role)

        val container = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            setPadding(64, 24, 64, 8)
            addView(passwordInput)
            if (!isFiltered) {
                addView(label("Блок (участок)"))
                addView(picker.blockRadio)
            }
            addView(label("Должность"))
            addView(picker.roleRadio)
        }

        AlertDialog.Builder(this)
            .setTitle("Изменить: ${user.full_name}")
            .setView(container)
            .setPositiveButton("Сохранить") { _, _ ->
                val newPass = passwordInput.text.toString().trim()
                CoroutineScope(Dispatchers.IO).launch {
                    try {
                        app.apiClient.updateUser(
                            user.id,
                            UserUpdateRequest(
                                role = picker.selectedRole(),
                                block = picker.selectedBlock(),
                                password = newPass.ifEmpty { null }
                            )
                        )
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@UsersActivity, "Сохранено", Toast.LENGTH_SHORT).show()
                            loadUsers()
                        }
                    } catch (e: Exception) {
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@UsersActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun deleteUser(user: UserItem) {
        AlertDialog.Builder(this)
            .setTitle("Удалить?")
            .setMessage("Удалить ${user.full_name}?")
            .setPositiveButton("Удалить") { _, _ ->
                CoroutineScope(Dispatchers.IO).launch {
                    try {
                        app.apiClient.deleteUser(user.id)
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@UsersActivity, "Удалён", Toast.LENGTH_SHORT).show()
                            loadUsers()
                        }
                    } catch (e: Exception) {
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@UsersActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }
            .setNegativeButton("Отмена", null)
            .show()
    }
}