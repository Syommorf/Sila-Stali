package com.silastali.app.ui

import android.os.Bundle
import android.view.View
import android.widget.EditText
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.recyclerview.widget.LinearLayoutManager
import com.silastali.app.SilastaliApp
import com.silastali.app.data.OrderClaim
import com.silastali.app.data.OrderCompletion
import com.silastali.app.data.OrderDetail
import com.silastali.app.data.OrderItemDetail
import com.silastali.app.data.UserItem
import com.silastali.app.databinding.ActivityOrderDetailBinding
import com.silastali.app.ui.adapters.OrderItemAdapter
import kotlinx.coroutines.*

class OrderDetailActivity : AppCompatActivity() {
    private lateinit var binding: ActivityOrderDetailBinding
    private val app by lazy { application as SilastaliApp }
    private val prefs by lazy { getSharedPreferences("auth", MODE_PRIVATE) }
    private val isManager get() = prefs.getString("role", "") in listOf(RoleNames.MANAGER, RoleNames.ADMIN)

    private var orderId: Int = 0
    private var employeesCache: List<UserItem>? = null
    private val workerRoles = setOf("apprentice", "bender", "senior_bender")

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityOrderDetailBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        orderId = intent.getIntExtra("order_id", 0)
        supportActionBar?.title = intent.getStringExtra("order_number") ?: "Заказ"

        binding.rvItems.layoutManager = LinearLayoutManager(this)
        binding.tvHint.visibility = if (isManager) View.GONE else View.VISIBLE

        loadDetail()
    }

    override fun onResume() {
        super.onResume()
        app.apiClient.token = prefs.getString("token", null)
        loadDetail()
        invitePrompter.start()
    }

    override fun onPause() {
        super.onPause()
        invitePrompter.stop()
    }

    private val invitePrompter by lazy { InvitePrompter(this) }

    private fun loadDetail() {
        binding.progressBar.visibility = View.VISIBLE
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val detail = app.apiClient.getOrderDetail(orderId)
                try {
                    employeesCache = app.apiClient.getUsers()
                } catch (_: Exception) {
                    // список сотрудников обновим при следующем нажатии «Состав бригады»
                }
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    render(detail)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    binding.progressBar.visibility = View.GONE
                    Toast.makeText(this@OrderDetailActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun render(detail: OrderDetail) {
        binding.tvOrderTitle.text = detail.name.ifEmpty { "Заказ ${detail.order_number}" }
        val totalBend = detail.items.filter { it.needs_bending }.sumOf { it.quantity }
        val doneBend = detail.items.filter { it.needs_bending }.sumOf { it.done_quantity }
        val totalStagesTotal = detail.items.sumOf { it.stages.values.sumOf { s -> s.total } }
        val totalStagesDone = detail.items.sumOf { it.stages.values.sumOf { s -> s.done } }
        val percent = when {
            totalStagesTotal > 0 -> totalStagesDone * 100 / totalStagesTotal
            totalBend > 0 -> doneBend * 100 / totalBend
            else -> 0
        }
        binding.tvOrderSummary.text = "Согнуто: $doneBend из $totalBend · Осталось: ${totalBend - doneBend} · Выполнено: $percent%"

        val isClosed = detail.status == "closed"
        if (isManager && !isClosed) {
            binding.btnClose.visibility = View.VISIBLE
            binding.btnClose.setOnClickListener { confirmClose(detail) }
        } else {
            binding.btnClose.visibility = View.GONE
        }

        binding.tvEmpty.visibility = if (detail.items.isEmpty()) View.VISIBLE else View.GONE
        binding.rvItems.visibility = if (detail.items.isEmpty()) View.GONE else View.VISIBLE
        val myId = prefs.getInt("user_id", -1)
        val myBlock = prefs.getString("block", null)
        binding.rvItems.adapter = OrderItemAdapter(
            detail.items,
            isManager = isManager,
            myWorkerId = myId,
            myBlock = if (isManager) null else myBlock,
            isClosed = isClosed,
            onAction = { item -> handleItemAction(detail, item) },
            onMarkStage = { item ->
                if (isManager) showStageMarkDialog(detail, item, null)
                else showStageMarkDialog(detail, item, myBlock)
            },
            onRelease = { item -> confirmRelease(detail, item) },
            onCrew = { item -> showCrewDialog(detail, item, canManage = item.claim != null) },
            onClick = { item -> showHistoryDialog(item) }
        )
        if (!isManager) {
            binding.tvHint.visibility = View.VISIBLE
            binding.tvHint.text = "Все заказы видны. Серые детали ещё не на вашем этапе — помечайте синие."
        }
    }

    private fun showCrewDialog(detail: OrderDetail, item: OrderItemDetail, canManage: Boolean) {
        val claim = item.claim
        val crewNames = claim?.workers?.map { it.name } ?: listOfNotNull(claim?.worker_name)
        val crewLine = if (crewNames.isEmpty()) "—" else crewNames.joinToString(" · ")

        // просмотр бригады — мгновенно, без сети (доступен и соисполнителям)
        if (!canManage) {
            AlertDialog.Builder(this@OrderDetailActivity)
                .setTitle("Состав бригады")
                .setMessage("Деталь: ${item.part_number}\n\nБригада:\n${crewNames.joinToString("\n") { "• $it" }}")
                .setPositiveButton("ОК", null)
                .show()
            return
        }

        // список сотрудников предзагружен при открытии заказа — показываем сразу
        employeesCache?.let { cached ->
            showCrewPicker(detail, item, claim, crewLine, cached)
            return
        }

        val loading = AlertDialog.Builder(this@OrderDetailActivity)
            .setTitle("Состав бригады")
            .setMessage("Загружаем список сотрудников…")
            .setCancelable(false)
            .show()
        val api = app.apiClient
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val users = api.getUsers()
                employeesCache = users
                withContext(Dispatchers.Main) {
                    loading.dismiss()
                    showCrewPicker(detail, item, claim, crewLine, users)
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    loading.dismiss()
                    AlertDialog.Builder(this@OrderDetailActivity)
                        .setTitle("Состав бригады")
                        .setMessage("Бригада:\n${crewNames.joinToString("\n") { "• $it" }}\n\nНе удалось загрузить список сотрудников.\n\nОшибка: ${e.message}")
                        .setPositiveButton("ОК", null)
                        .show()
                }
            }
        }
    }

    private fun showCrewPicker(detail: OrderDetail, item: OrderItemDetail, claim: OrderClaim?, crewLine: String, full: List<UserItem>) {
        val users = full.filter { it.role in workerRoles && it.id != claim?.worker_id }
        val pendingIds: Set<Int> = claim?.pending?.mapNotNull { it.id }?.toSet() ?: emptySet()
        val current: Set<Int> = ((claim?.workers?.map { it.id } ?: emptyList()) +
                pendingIds)
            .filter { it != claim?.worker_id }
            .toSet()
        if (users.isEmpty()) {
            AlertDialog.Builder(this@OrderDetailActivity)
                .setTitle("Состав бригады")
                .setMessage("Бригада: $crewLine\n\nВ системе нет других сотрудников для назначения.")
                .setPositiveButton("ОК", null)
                .show()
            return
        }
        val selected = current.toMutableSet()

        // кастомные чекбоксы вместо setMessage+setMultiChoiceItems — гарантированный видимый список
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(64, 16, 64, 8)
        }
        container.addView(android.widget.TextView(this).apply {
            text = "Бригада: $crewLine"
            textSize = 13f
            setTextColor(0xFF555555.toInt())
            setPadding(0, 0, 0, 8)
        })
        val checks = users.map { u ->
            val invited = u.id in pendingIds
            android.widget.CheckBox(this).apply {
                text = if (invited) {
                    "${u.full_name.ifEmpty { u.username }} — ${RoleNames.displayName(u.role)} (ожидает ответа)"
                } else {
                    "${u.full_name.ifEmpty { u.username }} — ${RoleNames.displayName(u.role)}"
                }
                textSize = 15f
                isChecked = u.id in current
                setPadding(0, 6, 0, 6)
                setOnCheckedChangeListener { _, isChecked ->
                    if (isChecked) selected.add(u.id) else selected.remove(u.id)
                }
            }
        }
        checks.forEach { container.addView(it) }

        AlertDialog.Builder(this@OrderDetailActivity)
            .setTitle("Состав бригады · ${item.part_number}")
            .setView(container)
            .setPositiveButton("Сохранить") { _, _ -> saveCrew(detail, item, current, selected.toSet()) }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun saveCrew(detail: OrderDetail, item: OrderItemDetail, before: Set<Int>, after: Set<Int>) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                for (id in after - before) {
                    app.apiClient.addClaimParticipant(detail.order_id, item.id, id)
                }
                for (id in before - after) {
                    app.apiClient.removeClaimParticipant(detail.order_id, item.id, id)
                }
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@OrderDetailActivity, "Бригада обновлена", Toast.LENGTH_SHORT).show()
                    loadDetail()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@OrderDetailActivity, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun confirmRelease(detail: OrderDetail, item: OrderItemDetail) {
        if (item.claim?.worker_id != prefs.getInt("user_id", -1)) {
            Toast.makeText(this, "Отказаться можно только от своей детали", Toast.LENGTH_SHORT).show()
            return
        }
        AlertDialog.Builder(this)
            .setTitle("Отказ от гибки")
            .setMessage("${item.part_number} — деталь снова станет доступной другим. Отказаться?")
            .setPositiveButton("Отказаться") { _, _ ->
                CoroutineScope(Dispatchers.IO).launch {
                    try {
                        app.apiClient.releaseOrderItem(detail.order_id, item.id)
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@OrderDetailActivity, "Деталь возвращена", Toast.LENGTH_SHORT).show()
                            loadDetail()
                        }
                    } catch (e: Exception) {
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@OrderDetailActivity, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show()
                        }
                    }
                }
            }
            .setNegativeButton("Остаться", null)
            .show()
    }

    private fun handleItemAction(detail: OrderDetail, item: OrderItemDetail) {
        if (detail.status == "closed") {
            showHistoryDialog(item)
            return
        }
        if (!item.needs_bending) {
            Toast.makeText(this, "По этой детали гибка не предусмотрена", Toast.LENGTH_SHORT).show()
            return
        }
        if (item.remaining <= 0) {
            showHistoryDialog(item)
            return
        }
        val mine = item.claim?.completed_at == null && item.claim?.worker_id == prefs.getInt("user_id", -1)
        if (mine) {
            showItemDialog(detail, item)
        } else {
            claimItem(detail.order_id, item.id)
        }
    }

    private fun claimItem(orderId: Int, itemId: Int) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                app.apiClient.claimOrderItem(orderId, itemId)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@OrderDetailActivity, "Взято в работу. По завершении нажмите «Выполнено»", Toast.LENGTH_LONG).show()
                    loadDetail()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@OrderDetailActivity, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun showItemDialog(detail: OrderDetail, item: OrderItemDetail) {
        if (detail.status == "closed") {
            showHistoryDialog(item)
            return
        }
        if (!item.needs_bending) {
            Toast.makeText(this, "По этой детали гибка не предусмотрена", Toast.LENGTH_SHORT).show()
            return
        }
        if (item.remaining <= 0) {
            showHistoryDialog(item)
            return
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(64, 32, 64, 16)
        }
        val tvPart = TextView(this).apply {
            text = "${item.part_number} · осталось ${item.remaining}"
            textSize = 15f
            setPadding(0, 0, 0, 12)
        }
        container.addView(tvPart)

        val etQuantity = EditText(this).apply {
            hint = "Сколько согнуто (осталось: ${item.remaining})"
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
            setPadding(48, 32, 48, 32)
        }
        container.addView(etQuantity)

        val dialog = AlertDialog.Builder(this)
            .setTitle("Отметить выполнение")
            .setView(container)
            .setPositiveButton("Отметить") { _, _ ->
                val qty = etQuantity.text.toString().toIntOrNull()
                if (qty == null || qty <= 0) {
                    Toast.makeText(this, "Введите количество", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                complete(detail.order_id, item.id, qty, null)
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun showStageMarkDialog(detail: OrderDetail, item: OrderItemDetail, onlyStage: String? = null) {
        if (detail.status == "closed") {
            showHistoryDialog(item)
            return
        }
        val pendingStages = if (onlyStage != null) {
            val s = item.stages[onlyStage]
            if (s != null && s.total > 0 && s.done < s.total) listOf(onlyStage) else emptyList()
        } else {
            Stages.PROD_ORDER.filter { s ->
                item.stages[s]?.let { it.total > 0 && it.done < it.total } == true
            }
        }
        if (pendingStages.isEmpty()) {
            Toast.makeText(this, "По детали все стадии выполнены", Toast.LENGTH_SHORT).show()
            showHistoryDialog(item)
            return
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(64, 32, 64, 16)
        }
        container.addView(TextView(this).apply {
            text = "${item.part_number} · маршрут ${item.route}"
            textSize = 14f
            setPadding(0, 0, 0, 12)
        })

        val spinner = android.widget.Spinner(this)
        if (onlyStage == null) {
            spinner.adapter = android.widget.ArrayAdapter(
                this,
                android.R.layout.simple_spinner_dropdown_item,
                pendingStages.map { Stages.name(it) }
            )
            container.addView(spinner)
        }

        val etQuantity = EditText(this).apply {
            hint = "Количество"
            inputType = android.text.InputType.TYPE_CLASS_NUMBER
            setPadding(48, 32, 48, 32)
        }
        container.addView(etQuantity)

        AlertDialog.Builder(this)
            .setTitle("Отметить стадию")
            .setView(container)
            .setPositiveButton("Отметить") { _, _ ->
                val qty = etQuantity.text.toString().toIntOrNull()
                if (qty == null || qty <= 0) {
                    Toast.makeText(this, "Введите количество", Toast.LENGTH_SHORT).show()
                    return@setPositiveButton
                }
                val stage = onlyStage ?: pendingStages[spinner.selectedItemPosition]
                complete(detail.order_id, item.id, qty, null, stage)
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun showHistoryDialog(item: OrderItemDetail) {
        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(64, 24, 64, 8)
        }
        val header = TextView(this).apply {
            text = "${item.part_number} · выполнено ${item.done_quantity} из ${item.quantity}"
            textSize = 15f
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setPadding(0, 0, 0, 12)
        }
        container.addView(header)

        if (item.completions.isEmpty()) {
            container.addView(TextView(this).apply {
                text = "Отметок нет"
                textSize = 14f
                setPadding(0, 0, 0, 12)
            })
        }

        item.completions.forEach { c ->
            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = android.view.Gravity.CENTER_VERTICAL
                setPadding(0, 4, 0, 4)
            }
            val info = TextView(this).apply {
                val stageTag = if (c.stage.isNullOrEmpty()) "" else "[${Stages.name(c.stage)}] "
                text = "$stageTag${c.executor_name} — ${c.quantity} шт (${formatDateTime(c.completed_at)})"
                textSize = 14f
                layoutParams = LinearLayout.LayoutParams(0, LinearLayout.LayoutParams.WRAP_CONTENT, 1f)
            }
            row.addView(info)
            if (isManager || c.marked_by == prefs.getInt("user_id", -1)) {
                val btnDel = TextView(this).apply {
                    text = " ✕"
                    textSize = 18f
                    setTextColor(0xFFC62828.toInt())
                    setOnClickListener { confirmDeleteCompletion(c) }
                }
                row.addView(btnDel)
            }
            container.addView(row)
        }

        AlertDialog.Builder(this)
            .setTitle("История по детали")
            .setView(container)
            .setPositiveButton("ОК", null)
            .show()
    }

    private fun confirmDeleteCompletion(c: OrderCompletion) {
        AlertDialog.Builder(this)
            .setTitle("Удалить отметку?")
            .setMessage("${c.executor_name} — ${c.quantity} шт")
            .setPositiveButton("Удалить") { _, _ ->
                CoroutineScope(Dispatchers.IO).launch {
                    try {
                        app.apiClient.deleteOrderCompletion(c.id)
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@OrderDetailActivity, "Отметка удалена", Toast.LENGTH_SHORT).show()
                            loadDetail()
                        }
                    } catch (e: Exception) {
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@OrderDetailActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun confirmClose(detail: OrderDetail) {
        val remaining = detail.items.filter { it.needs_bending }.sumOf { it.remaining }
        AlertDialog.Builder(this)
            .setTitle("Закрыть заказ?")
            .setMessage(if (remaining > 0) "Не согнуто ещё $remaining шт. Всё равно закрыть?" else "Все позиции выполнены. Закрыть заказ?")
            .setPositiveButton("Закрыть") { _, _ ->
                CoroutineScope(Dispatchers.IO).launch {
                    try {
                        app.apiClient.closeOrder(detail.order_id)
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@OrderDetailActivity, "Заказ закрыт", Toast.LENGTH_SHORT).show()
                            loadDetail()
                        }
                    } catch (e: Exception) {
                        withContext(Dispatchers.Main) {
                            Toast.makeText(this@OrderDetailActivity, "Ошибка: ${e.message}", Toast.LENGTH_SHORT).show()
                        }
                    }
                }
            }
            .setNegativeButton("Отмена", null)
            .show()
    }

    private fun complete(orderId: Int, itemId: Int, qty: Int, executorId: Int?, stage: String? = null) {
        CoroutineScope(Dispatchers.IO).launch {
            try {
                app.apiClient.completeOrderItem(orderId, itemId, qty, executorId, null, stage)
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@OrderDetailActivity, "Отмечено", Toast.LENGTH_SHORT).show()
                    loadDetail()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@OrderDetailActivity, "Ошибка: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun formatDateTime(dt: String): String {
        return try {
            val parts = dt.split("T")
            if (parts.size == 2) {
                val dateParts = parts[0].split("-")
                val timeParts = parts[1].split(":")
                "${dateParts[2]}.${dateParts[1]} ${timeParts[0]}:${timeParts[1]}"
            } else dt
        } catch (e: Exception) {
            dt
        }
    }
}