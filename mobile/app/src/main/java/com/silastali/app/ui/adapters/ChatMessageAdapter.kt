package com.silastali.app.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.silastali.app.data.ChatMessage
import com.silastali.app.databinding.ItemMessageInBinding
import com.silastali.app.databinding.ItemMessageOutBinding
import com.silastali.app.ui.ChatTime

class ChatMessageAdapter(
    private val messages: List<ChatMessage>,
    private val myUserId: Int,
    private val showSenders: Boolean,
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    private val TYPE_IN = 0
    private val TYPE_OUT = 1

    override fun getItemViewType(position: Int): Int {
        return if (messages[position].sender_id == myUserId) TYPE_OUT else TYPE_IN
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return if (viewType == TYPE_OUT) {
            OutVH(ItemMessageOutBinding.inflate(inflater, parent, false))
        } else {
            InVH(ItemMessageInBinding.inflate(inflater, parent, false))
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        val message = messages[position]
        when (holder) {
            is OutVH -> {
                holder.binding.tvText.text = message.text
                holder.binding.tvTime.text = ChatTime.formatTime(message.created_at)
            }
            is InVH -> {
                holder.binding.tvSender.visibility = if (showSenders) View.VISIBLE else View.GONE
                holder.binding.tvSender.text = message.sender_name ?: "Удалён"
                holder.binding.tvText.text = message.text
                holder.binding.tvTime.text = ChatTime.formatTime(message.created_at)
            }
        }
    }

    override fun getItemCount() = messages.size

    class InVH(val binding: ItemMessageInBinding) : RecyclerView.ViewHolder(binding.root)
    class OutVH(val binding: ItemMessageOutBinding) : RecyclerView.ViewHolder(binding.root)
}