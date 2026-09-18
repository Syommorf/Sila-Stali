package com.silastali.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.SilastaliApp
import com.silastali.app.data.SpecOrder
import com.silastali.app.databinding.ActivityBlockOrdersBinding
import com.silastali.app.ui.adapters.BlockOrderAdapter

class BlockOrdersActivity : AppCompatActivity() {

    private lateinit var binding: ActivityBlockOrdersBinding
    private val app by lazy { application as SilastaliApp }
    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }
    private var block: String = Stages.LASER

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityBlockOrdersBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        block = intent.getStringExtra("block") ?: Stages.LASER
        supportActionBar?.title = Stages.name(block)
    }

    override fun onResume() {
        super.onResume()
        app.apiClient.token = prefs.getString("token", null)
        loadOrders()
    }

    private fun loadOrders() {
        val token = prefs.getString("token", null)
        if (token.isNullOrEmpty()) {
            binding.tvHint.visibility = View.VISIBLE
            binding.tvHint.text = "Сначала войдите как «Руководство» на главном экране"
            return
        }
        binding.progressBar.visibility = View.VISIBLE
        binding.tvHint.visibility = View.GONE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val orders = app.apiClient.getOrders(status = "open", block = block)
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.tvEmpty.visibility = if (orders.isEmpty()) View.VISIBLE else View.GONE
                    binding.rvOrders.visibility = if (orders.isEmpty()) View.GONE else View.VISIBLE
                    binding.rvOrders.layoutManager = LinearLayoutManager(this@BlockOrdersActivity)
                    binding.rvOrders.adapter = BlockOrderAdapter(orders) { openOrder(it) }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.tvHint.visibility = View.VISIBLE
                    binding.tvHint.text = if ((e.message ?: "").contains("401")) {
                        "Сессия истекла — войдите как «Руководство» на главном экране"
                    } else {
                        "Ошибка загрузки: ${e.message}"
                    }
                }
            }
        }
    }

    private fun openOrder(order: SpecOrder) {
        startActivity(Intent(this, OrderDetailActivity::class.java).apply {
            putExtra("order_id", order.order_id)
            putExtra("order_number", order.name.ifEmpty { "Заказ ${order.order_number}" })
        })
    }
}