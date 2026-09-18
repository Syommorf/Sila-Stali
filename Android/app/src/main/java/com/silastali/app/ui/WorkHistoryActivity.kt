package com.silastali.app.ui

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.SilastaliApp
import com.silastali.app.data.WorkItem
import com.silastali.app.databinding.ActivityWorkHistoryBinding
import com.silastali.app.ui.adapters.WorkAdapter
import kotlinx.coroutines.*

class WorkHistoryActivity : AppCompatActivity() {
    private lateinit var binding: ActivityWorkHistoryBinding
    private val app by lazy { application as SilastaliApp }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityWorkHistoryBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.rvWorks.layoutManager = LinearLayoutManager(this)
        binding.progressBar.visibility = android.view.View.VISIBLE
    }

    override fun onResume() {
        super.onResume()
        val token = getSharedPreferences("auth", MODE_PRIVATE).getString("token", null)
        app.apiClient.token = token
        loadWorks()
    }

    private fun loadWorks() {
        binding.progressBar.visibility = android.view.View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val works = app.apiClient.getMyWorks()
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = android.view.View.GONE
                    if (works.isEmpty()) {
                        binding.tvEmpty.visibility = android.view.View.VISIBLE
                        binding.rvWorks.visibility = android.view.View.GONE
                    } else {
                        binding.tvEmpty.visibility = android.view.View.GONE
                        binding.rvWorks.visibility = android.view.View.VISIBLE
                        binding.rvWorks.adapter = WorkAdapter(works)
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = android.view.View.GONE
                    binding.tvEmpty.visibility = android.view.View.VISIBLE
                    binding.tvEmpty.text = "Ошибка загрузки: ${e.message}"
                }
            }
        }
    }
}
