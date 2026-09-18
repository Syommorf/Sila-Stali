package com.silastali.app.ui

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.SilastaliApp
import com.silastali.app.databinding.ActivityMyStatsBinding
import com.silastali.app.ui.adapters.TimelineAdapter
import kotlinx.coroutines.*
import java.text.SimpleDateFormat
import java.util.*

class MyStatsActivity : AppCompatActivity() {
    private lateinit var binding: ActivityMyStatsBinding
    private val app by lazy { application as SilastaliApp }
    private var period = "today"

    private val fmt = SimpleDateFormat("yyyy-MM-dd", Locale.getDefault()).apply {
        timeZone = TimeZone.getTimeZone("Europe/Moscow")
    }

    private val mskCal = Calendar.getInstance(TimeZone.getTimeZone("Europe/Moscow"))

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMyStatsBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.rvPeriods.layoutManager = LinearLayoutManager(this)

        binding.btnPeriodToday.setOnClickListener { setPeriod("today") }
        binding.btnPeriodWeek.setOnClickListener { setPeriod("week") }
        binding.btnPeriodMonth.setOnClickListener { setPeriod("month") }
        binding.btnPeriodYear.setOnClickListener { setPeriod("year") }

        setPeriod("today")
    }

    private fun setPeriod(newPeriod: String) {
        period = newPeriod
        val cal = Calendar.getInstance(TimeZone.getTimeZone("Europe/Moscow"))
        var dateFrom: String
        var dateTo: String
        var groupBy = "day"

        when (newPeriod) {
            "today" -> {
                dateFrom = fmt.format(cal.time)
                dateTo = fmt.format(cal.time)
            }
            "week" -> {
                dateTo = fmt.format(cal.time)
                cal.add(Calendar.DAY_OF_MONTH, -6)
                dateFrom = fmt.format(cal.time)
            }
            "month" -> {
                cal.set(Calendar.DAY_OF_MONTH, 1)
                dateFrom = fmt.format(cal.time)
                cal.set(Calendar.DAY_OF_MONTH, cal.getActualMaximum(Calendar.DAY_OF_MONTH))
                dateTo = fmt.format(cal.time)
            }
            else -> {
                groupBy = "month"
                val year = cal.get(Calendar.YEAR)
                dateFrom = "$year-01-01"
                dateTo = "$year-12-31"
            }
        }

        binding.tvPeriodRange.text = "Период: $dateFrom — $dateTo"
        binding.tvListHeader.text = if (groupBy == "month") "Итоги по месяцам:" else "Итоги по дням:"
        loadStats(dateFrom, dateTo, groupBy)
    }

    private fun loadStats(dateFrom: String, dateTo: String, groupBy: String) {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val stats = app.apiClient.getMyStats(dateFrom, dateTo, groupBy)
                val order = app.apiClient.getMyOrderStats(dateFrom, dateTo)
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.tvOrderStats.text = "Гибка по заказам: " +
                        "${order.total_bent_quantity} дет. · ${order.marks} отм. · ${order.distinct_parts} поз."
                    binding.tvTotalQuantity.text = "Всего деталей: ${stats.total_quantity}"
                    binding.tvTotalWorks.text = "Всего работ: ${stats.total_works}"
                    binding.tvAvgDuration.text = "Ср. время: ${stats.avg_duration_minutes ?: "—"} мин"
                    binding.rvPeriods.adapter = TimelineAdapter(stats.periods)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@MyStatsActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }
}