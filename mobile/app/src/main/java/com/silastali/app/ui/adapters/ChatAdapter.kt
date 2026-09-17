package com.silastali.app.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.silastali.app.data.ChatItem
import com.silastali.app.databinding.ItemChatBinding
import com.silastali.app.ui.ChatTime

class ChatAdapter(
    private val chats: List<ChatItem>,
    private val onClick: (ChatItem) -> Unit,
) : RecyclerView.Adapter<ChatAdapter.VH>() {

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        return VH(ItemChatBinding.inflate(LayoutInflater.from(parent.context), parent, false))
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val chat = chats[position]
        holder.binding.apply {
            tvChatName.text = ChatAdapter.title(chat)
            val last = chat.last_message
            if (last != null) {
                val sender = if (chat.type == "dm") "" else "${last.sender_name ?: "?"}: "
                tvChatLast.text = "$sender${last.text}"
                tvChatTime.text = ChatTime.formatTime(last.created_at)
            } else {
                tvChatLast.text = "Сообщений нет"
                tvChatTime.text = ""
            }
            if (chat.unread_count > 0) {
                tvUnread.visibility = View.VISIBLE
                tvUnread.text = if (chat.unread_count > 99) "99+" else chat.unread_count.toString()
            } else {
                tvUnread.visibility = View.INVISIBLE
            }
            root.setOnClickListener { onClick(chat) }
        }
    }

    override fun getItemCount() = chats.size

    class VH(val binding: ItemChatBinding) : RecyclerView.ViewHolder(binding.root)

    companion object {
        fun title(chat: ChatItem): String {
            return when (chat.type) {
                "dm" -> chat.other_user_name ?: "Личный чат"
                else -> chat.name ?: "Чат"
            }
        }
    }
}