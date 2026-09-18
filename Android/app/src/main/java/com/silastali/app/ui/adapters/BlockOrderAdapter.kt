package com.silastali.app.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.silastali.app.data.SpecOrder
import com.silastali.app.databinding.ItemBlockOrderBinding
import com.silastali.app.ui.Stages

class BlockOrderAdapter(
    private val orders: List<SpecOrder>,
    private val onClick: ((SpecOrder) -> Unit)? = null
) : RecyclerView.Adapter<BlockOrderAdapter.VH>() {

    class VH(val binding: ItemBlockOrderBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemBlockOrderBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val order = orders[position]
        holder.binding.apply {
            tvTitle.text = order.name.ifBlank { "Заказ ${order.order_number}" }
            tvMeta.text = "№ ${order.order_number} · Позиций: ${order.total_items}"
            tvPercent.text = "Выполнено: ${order.percent}%"
            tvPercent.setTextColor(if (order.percent >= 100) 0xFF4CAF50.toInt() else 0xFFFFB347.toInt())

            val lines = Stages.PROD_ORDER.mapNotNull { s ->
                order.stages[s]?.let { if (it.total > 0) Stages.name(s) to it else null }
            }
            tvStages.text = when {
                lines.isEmpty() -> "Стадий по маршруту нет"
                else -> lines.joinToString(" · ") { "${it.first} ${it.second.done}/${it.second.total}" }
            }

            card.setCardBackgroundColor(if (order.percent >= 100) 0xFF24302A.toInt() else 0xFF232B33.toInt())
            root.setOnClickListener { onClick?.invoke(order) }
        }
    }

    override fun getItemCount() = orders.size
}