package com.silastali.app.ui

import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.SilastaliApp
import com.silastali.app.databinding.ActivityOrderStatsBinding
import com.silastali.app.ui.adapters.OrderStatsAdapter
import kotlinx.coroutines.*

class OrderStatsActivity : AppCompatActivity() {
    private lateinit var binding: ActivityOrderStatsBinding
    private val app by lazy { application as SilastaliApp }
    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityOrderStatsBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = "Статистика гибки по заказам"
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.rvStats.layoutManager = LinearLayoutManager(this)
        loadStats()
    }

    override fun onResume() {
        super.onResume()
        app.apiClient.token = prefs.getString("token", null)
        loadStats()
    }

    private fun loadStats() {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val rows = app.apiClient.getOrderStats()
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.tvEmpty.visibility = if (rows.isEmpty()) View.VISIBLE else View.GONE
                    binding.rvStats.visibility = if (rows.isEmpty()) View.GONE else View.VISIBLE
                    binding.rvStats.adapter = OrderStatsAdapter(rows)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@OrderStatsActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }
}