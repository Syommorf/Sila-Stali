package com.silastali.app.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.silastali.app.data.UserItem
import com.silastali.app.databinding.ItemPersonCheckBinding
import com.silastali.app.ui.RoleNames

class MemberPickerAdapter(
    private val users: List<UserItem>,
    private val single: Boolean,
) : RecyclerView.Adapter<MemberPickerAdapter.VH>() {

    private val checked = HashSet<Int>()

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): VH {
        return VH(ItemPersonCheckBinding.inflate(LayoutInflater.from(parent.context), parent, false))
    }

    override fun onBindViewHolder(holder: VH, position: Int) {
        val user = users[position]
        holder.binding.apply {
            tvPersonName.text = user.full_name
            val role = RoleNames.displayName(user.role)
            val block = user.block?.let { " · ${RoleNames.blockDisplayName(it)}" } ?: ""
            tvPersonSub.text = "$role$block"
            cbPick.setOnCheckedChangeListener(null)
            cbPick.isChecked = user.id in checked
            cbPick.setOnCheckedChangeListener { _, isChecked ->
                if (isChecked) {
                    if (single) {
                        checked.clear()
                        users.forEachIndexed { i, u ->
                            if (u.id != user.id) {
                                notifyItemChanged(i)
                            }
                        }
                    }
                    checked.add(user.id)
                } else {
                    checked.remove(user.id)
                }
            }
            root.setOnClickListener {
                cbPick.isChecked = !cbPick.isChecked
            }
        }
    }

    override fun getItemCount() = users.size

    fun selectedIds(): List<Int> = checked.toList()

    class VH(val binding: ItemPersonCheckBinding) : RecyclerView.ViewHolder(binding.root)
}