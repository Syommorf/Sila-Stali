package com.silastali.app.ui.adapters

import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.silastali.app.data.WorkItem
import com.silastali.app.databinding.ItemWorkBinding

class WorkAdapter(
    private val works: List<WorkItem>,
    private val onDelete: ((WorkItem) -> Unit)? = null
) : RecyclerView.Adapter<WorkAdapter.VH>() {

    class VH(val binding: ItemWorkBinding) : RecyclerView.ViewHolder(binding.root)

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        val binding = ItemWorkBinding.inflate(LayoutInflater.from(parent.context), parent, false)
        return VH(binding)
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val work = works[position]
        val partNumber = work.part_number ?: ""
        val quantity = work.quantity ?: 0
        val note = work.note ?: ""
        val startTime = work.start_time ?: ""
        val endTime = work.end_time
        val duration = work.duration_minutes
        val workerName = work.worker_name ?: ""
        holder.binding.apply {
            tvPartNumber.text = "Деталь: $partNumber"
            tvQuantity.text = "Кол-во: $quantity"
            if (note.isNotEmpty()) {
                tvNote.text = note
                tvNote.visibility = android.view.View.VISIBLE
            } else {
                tvNote.visibility = android.view.View.GONE
            }
            tvStartTime.text = formatDateTime(startTime)
            tvEndTime.text = if (endTime != null) "→ ${formatDateTime(endTime)}" else "В работе"
            tvDuration.text = if (duration != null) "${duration} мин" else ""
            if (workerName.isNotEmpty()) {
                tvWorkerName.text = workerName
                tvWorkerName.visibility = android.view.View.VISIBLE
            } else {
                tvWorkerName.visibility = android.view.View.GONE
            }
            if (onDelete != null) {
                btnDelete.visibility = android.view.View.VISIBLE
                btnDelete.setOnClickListener { onDelete?.invoke(work) }
            } else {
                btnDelete.visibility = android.view.View.GONE
            }
        }
    }

    override fun getItemCount() = works.size

    private fun formatDateTime(dt: String): String {
        return try {
            val parts = dt.split("T")
            if (parts.size == 2) {
                val dateParts = parts[0].split("-")
                val timeParts = parts[1].split(":")
                "${dateParts[2]}.${dateParts[1]}.${dateParts[0]} ${timeParts[0]}:${timeParts[1]}"
            } else dt
        } catch (e: Exception) {
            dt
        }
    }
}