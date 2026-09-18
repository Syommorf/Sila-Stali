package com.silastali.app.ui

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.silastali.app.SilastaliApp
import com.silastali.app.data.SyncManager
import com.silastali.app.data.WorkCreateRequest
import com.silastali.app.databinding.ActivityDetailEntryBinding
import kotlinx.coroutines.*
import java.text.SimpleDateFormat
import java.util.*

class DetailEntryActivity : AppCompatActivity() {
    private lateinit var binding: ActivityDetailEntryBinding
    private val app by lazy { application as SilastaliApp }
    private val syncManager by lazy { SyncManager(this, app.database, app.apiClient) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDetailEntryBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val sdfNow = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault()).apply {
            timeZone = TimeZone.getTimeZone("Europe/Moscow")
        }
        val startTime = sdfNow.format(Date())
        val prefilledPart = intent.getStringExtra("part_number")

        binding.tvStartTime.text = "Начало: $startTime"

        if (!prefilledPart.isNullOrEmpty()) {
            binding.etPartNumber.setText(prefilledPart)
        }

        binding.btnSave.setOnClickListener {
            val partNumber = binding.etPartNumber.text.toString().trim()
            val quantityStr = binding.etQuantity.text.toString().trim()
            val note = binding.etNote.text.toString().trim()

            if (partNumber.isEmpty()) {
                Toast.makeText(this, "Введите номер детали", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }
            if (quantityStr.isEmpty()) {
                Toast.makeText(this, "Введите количество", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val quantity = quantityStr.toIntOrNull()
            if (quantity == null || quantity <= 0) {
                Toast.makeText(this, "Некорректное количество", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            saveWork(partNumber, quantity, note, startTime)
        }
    }

    private fun saveWork(partNumber: String, quantity: Int, note: String, startTime: String) {
        val endTime = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault()).apply {
            timeZone = TimeZone.getTimeZone("Europe/Moscow")
        }.format(Date())
        val work = WorkCreateRequest(
            part_number = partNumber,
            quantity = quantity,
            note = note,
            start_time = startTime,
            end_time = endTime
        )

        binding.btnSave.isEnabled = false

        CoroutineScope(Dispatchers.IO).launch {
            try {
                if (syncManager.isOnline()) {
                    app.apiClient.createWork(work)
                } else {
                    app.database.workDao().insert(
                        com.silastali.app.data.db.PendingWork(
                            part_number = partNumber,
                            quantity = quantity,
                            note = note,
                            start_time = startTime,
                            end_time = endTime,
                            synced = false
                        )
                    )
                }
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@DetailEntryActivity, "Деталь сохранена", Toast.LENGTH_SHORT).show()
                    finish()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.btnSave.isEnabled = true
                    Toast.makeText(this@DetailEntryActivity, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: android.content.Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
    }
}
