package com.silastali.app.ui

import android.content.Intent
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Shader
import android.os.Bundle
import android.view.View
import android.widget.ArrayAdapter
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.silastali.app.BuildConfig
import com.silastali.app.R
import com.silastali.app.SilastaliApp
import com.silastali.app.data.EmployeeItem
import com.silastali.app.databinding.ActivityLoginBinding
import com.silastali.app.service.ChatUnreadService
import com.silastali.app.service.InvitePollService
import kotlinx.coroutines.*
import java.io.File

class LoginActivity : AppCompatActivity() {
    private lateinit var binding: ActivityLoginBinding
    private val app by lazy { application as SilastaliApp }
    private var contentShown = false
    private var pendingUpdateCheck = false
    private var employees: List<EmployeeItem> = emptyList()

    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityLoginBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.tvVersion.text = "Версия ${BuildConfig.VERSION_NAME}"

        showCrashLogIfPresent()

        binding.btnLogin.setOnClickListener { doChiefLogin() }
        binding.btnChief.setOnClickListener { showChiefPanel() }
        binding.btnModuleBender.setOnClickListener { showEmployeePanel(Stages.BENDER) }
        binding.btnModuleLaser.setOnClickListener { showEmployeePanel(Stages.LASER) }
        binding.btnModuleMech.setOnClickListener { showEmployeePanel(Stages.FITTER) }
        binding.btnModuleWeld.setOnClickListener { showEmployeePanel(Stages.WELDER) }
        binding.btnModuleStore.setOnClickListener { showEmployeePanel(Stages.STOREKEEPER) }
        binding.btnBackToRole.setOnClickListener { showRoleSelection() }
        binding.btnBenderBack.setOnClickListener { showRoleSelection() }
        binding.btnBenderLogin.setOnClickListener { doLoginBySurname() }

        val metalLabels = listOf(
            binding.tvBlockChief, binding.tvBlockLaser, binding.tvBlockBender,
            binding.tvBlockMech, binding.tvBlockWeld, binding.tvBlockStore,
        )
        metalLabels.forEach { tv ->
            tv.post {
                val density = resources.displayMetrics.density
                tv.paint.shader = LinearGradient(
                    0f, 0f, 0f, 52f * density,
                    Color.parseColor("#F7FAFC"), Color.parseColor("#7C8999"),
                    Shader.TileMode.CLAMP,
                )
                tv.invalidate()
            }
        }

        binding.progressBar.visibility = View.GONE
        if (BuildConfig.ENABLE_AUTO_UPDATE) {
            UpdateManager(this, app.apiClient) { pendingUpdateCheck = true }.checkAndPrompt {}
        }
        showContent()
    }

    override fun onResume() {
        super.onResume()
        requestNotificationPermissionIfNeeded()
        // вернулись из настроек после разрешения установки — проверяем обновление ещё раз
        if (pendingUpdateCheck && BuildConfig.ENABLE_AUTO_UPDATE
            && android.os.Build.VERSION.SDK_INT >= 26 && packageManager.canRequestPackageInstalls()
        ) {
            pendingUpdateCheck = false
            UpdateManager(this, app.apiClient) { pendingUpdateCheck = true }.checkAndPrompt { showContent() }
        }
    }

    private fun showContent() {
        if (contentShown) return
        contentShown = true
        runOnUiThread {
            binding.progressBar.visibility = View.GONE
            showRoleSelection()
        }
    }

    private fun hideAllPanels() {
        binding.roleContainer.visibility = View.GONE
        binding.loginContainer.visibility = View.GONE
        binding.benderContainer.visibility = View.GONE
    }

    private fun showRoleSelection() {
        hideAllPanels()
        binding.roleContainer.visibility = View.VISIBLE
    }

    private fun showChiefPanel() {
        hideAllPanels()
        binding.loginContainer.visibility = View.VISIBLE
    }

    private fun showEmployeePanel(block: String) {
        hideAllPanels()
        binding.tvEmployeeTitle.text = "Вход — ${Stages.name(block)}"
        binding.benderContainer.visibility = View.VISIBLE
        loadEmployees(block)
    }

    private fun loadEmployees(block: String) {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val list = app.apiClient.getEmployees(block)
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    if (list.isEmpty()) {
                        toast("Список сотрудников пуст")
                        showRoleSelection()
                        return@withContext
                    }
                    employees = list
                    val labels = list.map { "${it.full_name} — ${RoleNames.displayName(it.role)}" }
                    val adapter = ArrayAdapter(
                        this@LoginActivity,
                        android.R.layout.simple_list_item_1,
                        labels
                    )
                    binding.etEmployee.setAdapter(adapter)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    toast("Не удалось загрузить сотрудников: ${e.message}")
                    showRoleSelection()
                }
            }
        }
    }

    private fun doChiefLogin() {
        val password = binding.etPassword.text.toString().trim()
        if (password.isEmpty()) {
            Toast.makeText(this, "Введите пароль", Toast.LENGTH_SHORT).show()
            return
        }
        binding.progressBar.visibility = View.VISIBLE
        binding.btnLogin.isEnabled = false

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val response = app.apiClient.loginChief(password)
                app.apiClient.token = response.access_token

                prefs.edit()
                    .putString("token", response.access_token)
                    .putInt("user_id", response.user_id)
                    .putString("username", "")
                    .putString("full_name", response.full_name)
                    .putString("role", response.role)
                    .putString("block", response.block)
                    .apply()

                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled = true
                    openNextScreen(response.role)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.btnLogin.isEnabled = true
                    Toast.makeText(this@LoginActivity, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun doLoginBySurname() {
        val password = binding.etBenderPassword.text.toString().trim()
        val selectedText = binding.etEmployee.text.toString().trim()
        if (selectedText.isEmpty() || employees.none { "${it.full_name} — ${RoleNames.displayName(it.role)}" == selectedText }) {
            Toast.makeText(this, "Выберите сотрудника", Toast.LENGTH_SHORT).show()
            return
        }
        val employee = employees.first { "${it.full_name} — ${RoleNames.displayName(it.role)}" == selectedText }
        if (password.isEmpty()) {
            Toast.makeText(this, "Введите пароль", Toast.LENGTH_SHORT).show()
            return
        }
        binding.progressBar.visibility = View.VISIBLE
        binding.btnBenderLogin.isEnabled = false

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val response = app.apiClient.login(employee.username, password)
                app.apiClient.token = response.access_token

                prefs.edit()
                    .putString("token", response.access_token)
                    .putInt("user_id", response.user_id)
                    .putString("username", employee.username)
                    .putString("full_name", response.full_name)
                    .putString("role", response.role)
                    .putString("block", response.block)
                    .apply()

                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.btnBenderLogin.isEnabled = true
                    openNextScreen(response.role)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.btnBenderLogin.isEnabled = true
                    Toast.makeText(this@LoginActivity, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun toast(msg: String) {
        Toast.makeText(this@LoginActivity, msg, Toast.LENGTH_SHORT).show()
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (android.os.Build.VERSION.SDK_INT >= 33) {
            val hasToken = prefs.getString("token", null)?.isNotEmpty() == true
            if (hasToken
                && checkSelfPermission(android.Manifest.permission.POST_NOTIFICATIONS)
                != android.content.pm.PackageManager.PERMISSION_GRANTED
            ) {
                requestPermissions(arrayOf(android.Manifest.permission.POST_NOTIFICATIONS), 77)
            }
        }
    }

    private fun openNextScreen(role: String) {
        if (role in listOf("apprentice", "bender", "senior_bender")) {
            startService(InvitePollService.intent(this))
        }
        startService(ChatUnreadService.intent(this))
        val block = prefs.getString("block", null)
        val intent = when (role) {
            "admin" -> Intent(this, AdminActivity::class.java)
            "manager" -> Intent(this, ManagerActivity::class.java)
            else -> when (block) {
                Stages.LASER, Stages.FITTER, Stages.WELDER, Stages.STOREKEEPER ->
                    Intent(this, BlockOrdersActivity::class.java).putExtra("block", block)
                else -> Intent(this, BenderActivity::class.java)
            }
        }
        intent.flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TASK
        startActivity(intent)
        finish()
    }

    private fun showCrashLogIfPresent() {
        val file = File(filesDir, "crash.log")
        if (!file.exists()) return
        val text = file.readText()
        file.delete()
        AlertDialog.Builder(this)
            .setTitle("Приложение упало")
            .setMessage(text)
            .setPositiveButton("Понятно", null)
            .show()
    }
}