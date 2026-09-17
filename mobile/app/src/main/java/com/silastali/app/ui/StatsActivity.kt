package com.silastali.app.ui

import android.app.DatePickerDialog
import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.SilastaliApp
import com.silastali.app.data.TimelinePeriod
import com.silastali.app.databinding.ActivityStatsBinding
import com.silastali.app.ui.adapters.OrderStatsAdapter
import com.silastali.app.ui.adapters.TimelineAdapter
import com.silastali.app.ui.adapters.WorkerStatsAdapter
import kotlinx.coroutines.*
import java.text.SimpleDateFormat
import java.util.*

class StatsActivity : AppCompatActivity() {
    private lateinit var binding: ActivityStatsBinding
    private val app by lazy { application as SilastaliApp }
    private var dateFrom: String? = null
    private var dateTo: String? = null
    private var period = "day"

    private val fmt = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).apply {
        timeZone = TimeZone.getTimeZone("Europe/Moscow")
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityStatsBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Статистика"
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.rvWorkerStats.layoutManager = LinearLayoutManager(this)
        binding.rvOrderStats.layoutManager = LinearLayoutManager(this)

        binding.btnDateFrom.setOnClickListener { pickDate(true) }
        binding.btnDateTo.setOnClickListener { pickDate(false) }
        binding.btnApplyFilter.setOnClickListener { loadStats() }

        binding.btnPeriodDay.setOnClickListener { setPeriod("day") }
        binding.btnPeriodMonth.setOnClickListener { setPeriod("month") }
        binding.btnPeriodYear.setOnClickListener { setPeriod("year") }

        binding.btnExport.setOnClickListener {
            startActivity(Intent(this, ExportActivity::class.java))
        }
        binding.btnAllWorks.setOnClickListener {
            startActivity(Intent(this, AllWorksActivity::class.java))
        }

        setPeriod("day")
    }

    private fun setPeriod(newPeriod: String) {
        period = newPeriod
        val now = Calendar.getInstance(TimeZone.getTimeZone("Europe/Moscow"))
        val base = Calendar.getInstance(TimeZone.getTimeZone("Europe/Moscow"))
        if (dateFrom != null) {
            try {
                base.time = fmt.parse(dateFrom!!)
            } catch (e: Exception) {
                base.time = now.time
            }
        }

        when (newPeriod) {
            "day" -> {
                dateFrom = fmt.format(base.time)
                dateTo = fmt.format(base.time)
                binding.tvDateFrom.text = "От: $dateFrom"
                binding.tvDateTo.text = "До: $dateTo"
            }
            "month" -> {
                base.set(Calendar.DAY_OF_MONTH, 1)
                val start = fmt.format(base.time)
                base.set(Calendar.DAY_OF_MONTH, base.getActualMaximum(Calendar.DAY_OF_MONTH))
                val end = fmt.format(base.time)
                dateFrom = start
                dateTo = end
                binding.tvDateFrom.text = "От: $start"
                binding.tvDateTo.text = "До: $end"
            }
            "year" -> {
                val year = base.get(Calendar.YEAR)
                dateFrom = "$year-01-01"
                dateTo = "$year-12-31"
                binding.tvDateFrom.text = "От: $dateFrom"
                binding.tvDateTo.text = "До: $dateTo"
            }
        }
        loadStats()
    }

    private fun pickDate(isFrom: Boolean) {
        val cal = Calendar.getInstance(TimeZone.getTimeZone("Europe/Moscow"))
        if (isFrom) {
            if (dateFrom != null) {
                try { cal.time = fmt.parse(dateFrom!!) } catch (e: Exception) {}
            }
        } else if (dateTo != null) {
            try { cal.time = fmt.parse(dateTo!!) } catch (e: Exception) {}
        }
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

    private fun loadStats() {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val overview = app.apiClient.getStatsOverview(dateFrom, dateTo)
                val orderRows = app.apiClient.getOrderStats(dateFrom, dateTo)
                val byWorker = if (period == "day") {
                    app.apiClient.getStatsByWorker(dateFrom, dateTo)
                } else {
                    emptyList()
                }
                val timeline = if (period == "day") {
                    emptyList()
                } else {
                    app.apiClient.getStatsTimeline(
                        if (period == "month") "day" else "month",
                        dateFrom, dateTo
                    )
                }
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.tvOrderHeader.text = if (orderRows.isEmpty()) {
                        "Гибка по заказам: без отметок"
                    } else {
                        "Гибка по заказам (${orderRows.size}):"
                    }
                    binding.rvOrderStats.adapter = OrderStatsAdapter(orderRows)
                    binding.tvTotalQuantity.text = "Всего деталей: ${overview.total_quantity}"
                    binding.tvTotalWorks.text = "Всего работ: ${overview.total_works}"
                    binding.tvTotalWorkers.text = "Рабочих: ${overview.total_workers}"
                    binding.tvAvgDuration.text = "Ср. время: ${overview.avg_duration_minutes ?: "—"} мин"
                    if (period == "day") {
                        binding.tvListHeader.text = "По рабочим:"
                        binding.rvWorkerStats.adapter = WorkerStatsAdapter(byWorker)
                    } else {
                        binding.tvListHeader.text = if (period == "month") "По дням:" else "По месяцам:"
                        binding.rvWorkerStats.adapter = TimelineAdapter(timeline)
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@StatsActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }
}