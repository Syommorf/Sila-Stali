package com.silastali.app.ui.adapters

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.silastali.app.data.TimelinePeriod
import com.silastali.app.databinding.ItemTimelineBinding

class TimelineAdapter(private val periods: List<TimelinePeriod>) : RecyclerView.Adapter<TimelineAdapter.VH>() {

    class VH(val binding: ItemTimelineBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemTimelineBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val item = periods[position]
        holder.binding.apply {
            tvPeriod.text = formatPeriod(item.period)
            tvTotal.text = "Деталей: ${item.total_quantity}  ·  Работ: ${item.total_works}"
        }
    }

    override fun getItemCount() = periods.size

    private fun formatPeriod(period: String): String {
        return try {
            val parts = period.split("-")
            when (parts.size) {
                3 -> "${parts[2]}.${parts[1]}.${parts[0]}"   // день
                2 -> "${parts[1]}.${parts[0]}"               // месяц
                else -> period
            }
        } catch (e: Exception) {
            period
        }
    }
}