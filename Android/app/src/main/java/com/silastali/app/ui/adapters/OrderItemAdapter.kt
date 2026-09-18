package com.silastali.app.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.silastali.app.data.OrderItemDetail
import com.silastali.app.databinding.ItemOrderItemBinding
import com.silastali.app.ui.Stages

class OrderItemAdapter(
    private val items: List<OrderItemDetail>,
    private val isManager: Boolean = false,
    private val myWorkerId: Int = -1,
    private val myBlock: String? = null,
    private val isClosed: Boolean = false,
    private val onAction: ((OrderItemDetail) -> Unit)? = null,
    private val onMarkStage: ((OrderItemDetail) -> Unit)? = null,
    private val onRelease: ((OrderItemDetail) -> Unit)? = null,
    private val onCrew: ((OrderItemDetail) -> Unit)? = null,
    private val onClick: ((OrderItemDetail) -> Unit)? = null
) : RecyclerView.Adapter<OrderItemAdapter.VH>() {

    class VH(val binding: ItemOrderItemBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemOrderItemBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = items[position]
        holder.binding.apply {
            tvPartNumber.text = item.part_number.ifEmpty { "Деталь —" }
            tvQuantity.text = "${item.quantity} шт."
            val thickness = item.thickness
            tvSpec.text = "Толщина: ${if (thickness != null) formatFloat(thickness) else "—"} · Марка: ${item.steel_grade.ifEmpty { "—" }} · Маршрут: ${item.route.ifEmpty { "—" }}"

            val done = item.stage_done || (item.stages.isEmpty() && item.quantity > 0 && item.done_quantity >= item.quantity)
            val claim = item.claim
            val open = claim != null && claim.completed_at == null
            val mine = claim?.worker_id == myWorkerId
            val inWork = open
            val active = item.active
            val isInactive = !isManager && !active
            var workerMark = false

            val displayRemaining = if (item.stages.isNotEmpty())
                item.stages.values.sumOf { maxOf(0, it.total - it.done) }
            else item.remaining
            tvProgress.text = if (done) "✅ ГОТОВО · ${item.quantity} из ${item.quantity}" else "Выполнено: ${item.done_quantity} · Осталось: $displayRemaining"
            tvProgress.setTextColor(
                when {
                    isInactive -> 0xFF8A96A3.toInt()
                    done -> 0xFF4CAF50.toInt()
                    else -> 0xFFFFB347.toInt()
                }
            )
            tvPartNumber.setTextColor(if (isInactive) 0xFF8A96A3.toInt() else 0xFFEDF2F7.toInt())
            tvQuantity.setTextColor(if (isInactive) 0xFF8A96A3.toInt() else 0xFF4FC3F7.toInt())
            tvSpec.setTextColor(if (isInactive) 0xFF7A8794.toInt() else 0xFFA9B7C6.toInt())

            // Строка стадий (показываем если есть данные по стадиям)
            val stagesMap = item.stages
            if (stagesMap.isNotEmpty()) {
                val lines = Stages.PROD_ORDER.mapNotNull { s ->
                    stagesMap[s]?.let { if (it.total > 0) Pair(Stages.name(s), it) else null }
                }
                if (lines.isNotEmpty()) {
                    tvStages.visibility = View.VISIBLE
                    tvStages.text = lines.joinToString(" · ") { "${it.first} ${it.second.done}/${it.second.total}" }
                } else {
                    tvStages.visibility = View.GONE
                }
            } else if (item.untracked_route) {
                tvStages.visibility = View.VISIBLE
                tvStages.text = "Маршрут не отслеживается"
            } else {
                tvStages.visibility = View.GONE
            }

            val crewNames = claim?.workers?.map { it.name }
                ?: if (claim != null) listOf(claim.worker_name) else emptyList()
            val crewText = if (crewNames.size > 1) crewNames.joinToString(" · ") else (claim?.worker_name ?: "")
            tvClaim.text = when {
                claim == null -> ""
                done || claim.completed_at != null ->
                    "Взяли: ${crewText} · Завершил(а): ${formatDateTime(claim.completed_at)}"
                else -> "В работе: ${crewText} · взял(а) ${formatDateTime(claim.claimed_at)}"
            }
            tvClaim.setTextColor(if (open) 0xFFFFB347.toInt() else 0xFFA9B7C6.toInt())

            if (done || isClosed) {
                btnAction.visibility = View.GONE
                crewRow.visibility = View.GONE
            } else if (isInactive) {
                btnAction.visibility = View.GONE
                crewRow.visibility = View.GONE
            } else if (isManager) {
                btnAction.visibility = View.VISIBLE
                btnAction.text = "Отметить стадию"
                btnAction.backgroundTintList = android.content.res.ColorStateList.valueOf(0xFF1976D2.toInt())
                btnAction.isEnabled = true
                crewRow.visibility = View.GONE
                btnAction.setOnClickListener { onMarkStage?.invoke(item) }
            } else if (open && mine) {
                btnAction.visibility = View.VISIBLE
                btnAction.text = "✅ Выполнено"
                btnAction.backgroundTintList = android.content.res.ColorStateList.valueOf(0xFF4CAF50.toInt())
                btnAction.isEnabled = true
                crewRow.visibility = View.VISIBLE
                btnRelease.visibility = View.VISIBLE
            } else if (open && !mine) {
                btnAction.visibility = View.GONE
                crewRow.visibility = View.VISIBLE
                btnRelease.visibility = View.GONE
            } else if (myBlock == null || myBlock == Stages.BENDER) {
                btnAction.visibility = View.VISIBLE
                btnAction.text = "🚀 Взять в работу"
                btnAction.backgroundTintList = android.content.res.ColorStateList.valueOf(0xFFF9A825.toInt())
                btnAction.isEnabled = true
                crewRow.visibility = View.GONE
            } else {
                val stageLabel = Stages.name(myBlock ?: "")
                workerMark = true
                btnAction.visibility = View.VISIBLE
                btnAction.text = "📌 Отметить: $stageLabel"
                btnAction.backgroundTintList = android.content.res.ColorStateList.valueOf(0xFF1976D2.toInt())
                btnAction.isEnabled = true
                crewRow.visibility = View.GONE
            }

            card.setCardBackgroundColor(
                when {
                    isInactive -> 0xFF2A2E33.toInt()
                    done -> 0xFF24302A.toInt()
                    inWork -> 0xFF33302A.toInt()
                    else -> 0xFF232B33.toInt()
                }
            )

            if (isInactive) {
                btnAction.visibility = View.GONE
                crewRow.visibility = View.GONE
            }

            if (!isManager) {
                btnAction.setOnClickListener {
                    if (workerMark) onMarkStage?.invoke(item) else onAction?.invoke(item)
                }
            }
            btnRelease.setOnClickListener { onRelease?.invoke(item) }
            btnCrew.setOnClickListener { onCrew?.invoke(item) }
            root.setOnClickListener { onClick?.invoke(item) }
        }
    }

    override fun getItemCount() = items.size

    private fun formatFloat(v: Double): String {
        return if (v == v.toInt().toDouble()) v.toInt().toString() else v.toString()
    }

    private fun formatDateTime(dt: String?): String {
        if (dt.isNullOrEmpty()) return ""
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