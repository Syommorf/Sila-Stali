package com.silastali.app.ui

import android.app.DatePickerDialog
import android.app.DownloadManager
import android.content.Context
import android.net.Uri
import android.os.Bundle
import android.os.Environment
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.silastali.app.SilastaliApp
import com.silastali.app.databinding.ActivityExportBinding
import java.text.SimpleDateFormat
import java.util.*

class ExportActivity : AppCompatActivity() {
    private lateinit var binding: ActivityExportBinding
    private val app by lazy { application as SilastaliApp }
    private var dateFrom: String? = null
    private var dateTo: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityExportBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Экспорт в Excel"
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.btnDateFrom.setOnClickListener { pickDate(true) }
        binding.btnDateTo.setOnClickListener { pickDate(false) }
        binding.btnExport.setOnClickListener { exportExcel() }
    }

    private fun pickDate(isFrom: Boolean) {
        val cal = Calendar.getInstance()
        DatePickerDialog(this, { _, y, m, d ->
            val date = String.format("%04d-%02d-%02d", y, m + 1, d)
            if (isFrom) {
                dateFrom = date
                binding.tvDateFrom.text = "От: $date"
            } else {
                dateTo = date
                binding.tvDateTo.text = "До: $date"
            }
        }, cal.get(Calendar.YEAR), cal.get(Calendar.MONTH), cal.get(Calendar.DAY_OF_MONTH)).show()
    }

    private fun exportExcel() {
        val url = app.apiClient.getExportUrl(dateFrom, dateTo)
        val request = DownloadManager.Request(Uri.parse(url))
            .setTitle("Экспорт работ")
            .setDescription("Скачивание Excel-файла...")
            .setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED)
            .setDestinationInExternalPublicDir(
                Environment.DIRECTORY_DOWNLOADS,
                "works_${SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).apply { timeZone = TimeZone.getTimeZone("Europe/Moscow") }.format(Date())}.xlsx"
            )
            .addRequestHeader("Authorization", "Bearer ${app.apiClient.token}")

        val dm = getSystemService(Context.DOWNLOAD_SERVICE) as DownloadManager
        dm.enqueue(request)
        Toast.makeText(this, "Скачивание начато", Toast.LENGTH_SHORT).show()
        finish()
    }
}
