package com.silastali.app.ui

import android.content.Intent
import android.os.Bundle
import android.view.View
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.SilastaliApp
import com.silastali.app.data.SpecOrder
import com.silastali.app.databinding.ActivityOrderListBinding
import com.silastali.app.ui.adapters.OrderAdapter
import kotlinx.coroutines.*

class OrderListActivity : AppCompatActivity() {
    private lateinit var binding: ActivityOrderListBinding
    private val app by lazy { application as SilastaliApp }
    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }
    private var archived = false
    private val isManager get() = prefs.getString("role", "") in listOf(RoleNames.MANAGER, RoleNames.ADMIN)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityOrderListBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        supportActionBar?.title = if (isManager) "Просмотр заказа" else "Заказы на гибку"
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.rvOrders.layoutManager = LinearLayoutManager(this)

        if (isManager) {
            binding.btnStats.visibility = View.VISIBLE
            binding.tabRow.visibility = View.VISIBLE
            binding.btnTabCurrent.setOnClickListener {
                archived = false
                updateTabs()
                loadOrders()
            }
            binding.btnTabArchive.setOnClickListener {
                archived = true
                updateTabs()
                loadOrders()
            }
        }

        binding.btnUpload.setOnClickListener { pickSpecFile() }
        binding.btnStats.setOnClickListener {
            startActivity(Intent(this, OrderStatsActivity::class.java))
        }

        updateTabs()
        loadOrders()
    }

    private fun updateTabs() {
        binding.btnTabCurrent.backgroundTintList =
            android.content.res.ColorStateList.valueOf(if (!archived) 0xFF2E7D32.toInt() else 0xFFBDBDBD.toInt())
        binding.btnTabArchive.backgroundTintList =
            android.content.res.ColorStateList.valueOf(if (archived) 0xFF6A1B9A.toInt() else 0xFFBDBDBD.toInt())
    }

    override fun onResume() {
        super.onResume()
        app.apiClient.token = prefs.getString("token", null)
        loadOrders()
        invitePrompter.start()
    }

    override fun onPause() {
        super.onPause()
        invitePrompter.stop()
    }

    private val invitePrompter by lazy { InvitePrompter(this) }

    private fun loadOrders() {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val orders = if (archived) app.apiClient.getOrders("ready") else app.apiClient.getOrders()
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    binding.tvEmpty.visibility = if (orders.isEmpty()) View.VISIBLE else View.GONE
                    binding.tvEmpty.text = if (archived) "В архиве пока нет заказов" else "Заказов нет"
                    binding.rvOrders.visibility = if (orders.isEmpty()) View.GONE else View.VISIBLE
                    binding.rvOrders.adapter = OrderAdapter(
                        orders,
                        onClick = { order -> openOrder(order) },
                        onReady = if (isManager) { order -> confirmReady(order) } else null,
                        onDelete = if (isManager) { order -> confirmDelete(order) } else null
                    )
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@OrderListActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun confirmReady(order: SpecOrder) {
        android.app.AlertDialog.Builder(this)
            .setTitle("Отметить заказ готовым?")
            .setMessage("${order.name.ifEmpty { "Заказ ${order.order_number}" }}\n" +
                "Согнуто ${order.done_bend_quantity} из ${order.total_bend_quantity}.\n" +
                "Заказ уйдёт в архив «готовые» (хранится год).")
            .setPositiveButton("✅ Готов") { _, _ -> markReady(order) }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun markReady(order: SpecOrder) {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                app.apiClient.markOrderReady(order.order_id)
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@OrderListActivity, "Заказ в архиве", Toast.LENGTH_SHORT).show()
                    loadOrders()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@OrderListActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun confirmDelete(order: SpecOrder) {
        android.app.AlertDialog.Builder(this)
            .setTitle("Удалить заказ?")
            .setMessage("${order.name.ifEmpty { "Заказ ${order.order_number }" }}\n" +
                "Будут удалены позиции и все отметки о гибке. Действие необратимо.")
            .setPositiveButton("🗑 Удалить") { _, _ -> deleteOrder(order) }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun deleteOrder(order: SpecOrder) {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                app.apiClient.deleteOrder(order.order_id)
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@OrderListActivity, "Заказ удалён", Toast.LENGTH_SHORT).show()
                    loadOrders()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@OrderListActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun openOrder(order: SpecOrder) {
        val intent = Intent(this, OrderDetailActivity::class.java).apply {
            putExtra("order_id", order.order_id)
            putExtra("order_number", order.name.ifEmpty { "Заказ ${order.order_number}" })
        }
        startActivity(intent)
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
                val msg = result.orders.joinToString("; ") {
                    "${it.name}: создан (${it.items} поз., ${it.bending_items} с гибкой)"
                }
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@OrderListActivity, msg, Toast.LENGTH_LONG).show()
                    loadOrders()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@OrderListActivity, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
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