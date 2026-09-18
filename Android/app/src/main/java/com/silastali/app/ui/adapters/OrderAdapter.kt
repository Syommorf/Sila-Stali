package com.silastali.app.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.silastali.app.data.SpecOrder
import com.silastali.app.databinding.ItemOrderBinding

class OrderAdapter(
    private val orders: List<SpecOrder>,
    private val onClick: ((SpecOrder) -> Unit)? = null,
    private val onReady: ((SpecOrder) -> Unit)? = null,
    private val onDelete: ((SpecOrder) -> Unit)? = null
) : RecyclerView.Adapter<OrderAdapter.VH>() {

    class VH(val binding: ItemOrderBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemOrderBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val order = orders[position]
        holder.binding.apply {
            tvOrderNumber.text = order.name.ifEmpty { "Заказ ${order.order_number}" }
            tvOrderName.text = "Позиций: ${order.total_items} · с гибкой: ${order.bending_items}"
            tvOrderProgress.text = "Согнуто: ${order.done_bend_quantity} из ${order.total_bend_quantity}"
            tvOrderRemaining.text = "Осталось согнуть: ${order.remaining_bend_quantity}"
            val isFinished = order.status == "ready" ||
                (order.total_bend_quantity > 0 && order.remaining_bend_quantity <= 0)
            tvStatus.text = if (isFinished) "ГОТОВ" else "ОТКРЫТ"
            tvStatus.setTextColor(
                if (isFinished) 0xFF4CAF50.toInt() else 0xFFFFB347.toInt()
            )
            card.setCardBackgroundColor(if (isFinished) 0xFF24302A.toInt() else 0xFF232B33.toInt())
            btnReady.visibility = if (onReady != null && !isFinished) View.VISIBLE else View.GONE
            btnDelete.visibility = if (onDelete != null) View.VISIBLE else View.GONE
            btnRow.visibility = if (btnReady.visibility == View.VISIBLE || btnDelete.visibility == View.VISIBLE)
                View.VISIBLE else View.GONE
            btnReady.setOnClickListener { onReady?.invoke(order) }
            btnDelete.setOnClickListener { onDelete?.invoke(order) }
            root.setOnClickListener { onClick?.invoke(order) }
        }
    }

    override fun getItemCount() = orders.size
}