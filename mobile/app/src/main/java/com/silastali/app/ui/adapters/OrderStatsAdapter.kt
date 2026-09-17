package com.silastali.app.ui.adapters

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.silastali.app.data.OrderStatsRow
import com.silastali.app.databinding.ItemOrderStatBinding

class OrderStatsAdapter(
    private val rows: List<OrderStatsRow>
) : RecyclerView.Adapter<OrderStatsAdapter.VH>() {

    class VH(val binding: ItemOrderStatBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemOrderStatBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val row = rows[position]
        holder.binding.apply {
            tvWorkerName.text = row.worker_name.ifEmpty { "Рабочий #${row.worker_id}" }
            tvBentQty.text = "Согнуто деталей: ${row.total_bent_quantity}"
            tvMarks.text = "Отметок: ${row.marks} · Деталей в заказах: ${row.distinct_parts}"
        }
    }

    override fun getItemCount() = rows.size
}