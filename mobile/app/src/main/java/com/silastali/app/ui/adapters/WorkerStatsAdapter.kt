package com.silastali.app.ui.adapters

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.silastali.app.data.WorkerStat
import com.silastali.app.databinding.ItemWorkerStatBinding

class WorkerStatsAdapter(private val stats: List<WorkerStat>) : RecyclerView.Adapter<WorkerStatsAdapter.VH>() {

    class VH(val binding: ItemWorkerStatBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemWorkerStatBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val stat = stats[position]
        holder.binding.apply {
            tvWorkerName.text = stat.worker_name
            tvTotalQty.text = "Деталей: ${stat.total_quantity}"
            tvTotalWorks.text = "Работ: ${stat.total_works}"
            tvAvgDuration.text = "Ср. время: ${stat.avg_duration_minutes ?: "—"} мин"
            val partsText = stat.parts_breakdown.entries.joinToString("\n") { "${it.key}: ${it.value}" }
            tvPartsBreakdown.text = partsText
        }
    }

    override fun getItemCount() = stats.size
}
