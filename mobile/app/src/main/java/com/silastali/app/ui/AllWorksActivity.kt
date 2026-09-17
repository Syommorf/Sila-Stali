package com.silastali.app.ui

import android.app.DatePickerDialog
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.SilastaliApp
import com.silastali.app.data.WorkItem
import com.silastali.app.databinding.ActivityAllWorksBinding
import com.silastali.app.ui.adapters.WorkAdapter
import kotlinx.coroutines.*
import java.util.*

class AllWorksActivity : AppCompatActivity() {
    private lateinit var binding: ActivityAllWorksBinding
    private val app by lazy { application as SilastaliApp }
    private var dateFrom: String? = null
    private var dateTo: String? = null
    private var partFilter: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityAllWorksBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Все работы"
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.rvWorks.layoutManager = LinearLayoutManager(this)

        binding.btnDateFrom.setOnClickListener { pickDate(true) }
        binding.btnDateTo.setOnClickListener { pickDate(false) }
        binding.btnFilter.setOnClickListener {
            partFilter = binding.etPartFilter.text.toString().trim().ifEmpty { null }
            loadWorks()
        }
        binding.btnClearFilter.setOnClickListener {
            dateFrom = null
            dateTo = null
            partFilter = null
            binding.etPartFilter.setText("")
            binding.tvDateFrom.text = "От:"
            binding.tvDateTo.text = "До:"
            loadWorks()
        }

        loadWorks()
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

    private fun confirmDeleteWork(work: WorkItem) {
        AlertDialog.Builder(this)
            .setTitle("Удаление работы")
            .setMessage("Вы точно хотите удалить работу гибщика?")
            .setPositiveButton("Удалить") { _, _ -> deleteWork(work) }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun deleteWork(work: WorkItem) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                app.apiClient.deleteWork(work.id)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@AllWorksActivity, "Работа удалена", Toast.LENGTH_SHORT).show()
                    loadWorks()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@AllWorksActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun loadWorks() {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val works = app.apiClient.getWorks(dateFrom, dateTo, partNumber = partFilter)
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.tvEmpty.visibility = if (works.isEmpty()) View.VISIBLE else View.GONE
                    binding.rvWorks.visibility = if (works.isEmpty()) View.GONE else View.VISIBLE
                    binding.rvWorks.adapter = WorkAdapter(works, { work -> confirmDeleteWork(work) })
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@AllWorksActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }
}
