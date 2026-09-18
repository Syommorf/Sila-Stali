package com.silastali.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import com.silastali.app.SilastaliApp
import com.silastali.app.databinding.ActivityUploadOrderBinding
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class UploadOrderActivity : AppCompatActivity() {
    private lateinit var binding: ActivityUploadOrderBinding
    private val app by lazy { application as SilastaliApp }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityUploadOrderBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.btnChooseFile.setOnClickListener { pickSpecFile() }
    }

    private fun pickSpecFile() {
        val intent = Intent(Intent.ACTION_OPEN_DOCUMENT).apply {
            addCategory(Intent.CATEGORY_OPENABLE)
            type = "*/*"
            putExtra(Intent.EXTRA_MIME_TYPES, arrayOf(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "application/vnd.ms-excel",
                "application/octet-stream"
            ))
        }
        startActivityForResult(intent, 300)
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == 300 && resultCode == RESULT_OK) {
            val uri = data?.data ?: return
            uploadSpec(uri)
        }
    }

    private fun uploadSpec(uri: android.net.Uri) {
        binding.progressBar.visibility = View.VISIBLE
        Toast.makeText(this, "Загрузка спецификации...", Toast.LENGTH_SHORT).show()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val resolver = contentResolver
                val fileName = uri.getDisplayName(resolver) ?: "spec.xlsx"
                val bytes = resolver.openInputStream(uri)?.use { it.readBytes() }
                    ?: throw Exception("Не удалось прочитать файл")
                val result = app.apiClient.uploadOrderSpec(fileName, bytes)
                val created = result.orders.filter { it.status != "exists" }
                val existing = result.orders.filter { it.status == "exists" }
                val msg = buildString {
                    val parts = mutableListOf<String>()
                    if (created.isNotEmpty()) {
                        parts += created.joinToString("; ") { "${it.name}: создано ${it.items} поз." }
                    }
                    if (existing.isNotEmpty()) {
                        parts += "Уже есть: ${existing.joinToString("; ") { it.name }}"
                    }
                    append(parts.joinToString(". "))
                    if (isEmpty()) append("Файл обработан, новых данных нет")
                }
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.tvResult.visibility = View.VISIBLE
                    binding.tvResult.text = msg
                    Toast.makeText(this@UploadOrderActivity, msg, Toast.LENGTH_LONG).show()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.tvResult.visibility = View.VISIBLE
                    val errorMsg = e.message ?: "Неизвестная ошибка"
                    binding.tvResult.text = "Ошибка: $errorMsg"
                    showRetryDialog(uri, errorMsg)
                }
            }
        }
    }

    private fun showRetryDialog(uri: android.net.Uri, errorMsg: String) {
        if (isFinishing) return
        AlertDialog.Builder(this)
            .setTitle("Загрузка не удалась")
            .setMessage("$errorMsg\n\nПовторить попытку?")
            .setPositiveButton("Повторить") { _, _ -> uploadSpec(uri) }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun android.net.Uri.getDisplayName(resolver: android.content.ContentResolver): String? {
        var name: String? = null
        try {
            resolver.query(this, arrayOf(android.provider.OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
                if (c.moveToFirst()) name = c.getString(0)
            }
        } catch (_: Exception) {
        }
        return name
    }
}