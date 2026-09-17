package com.silastali.app.ui.adapters

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.recyclerview.widget.RecyclerView
import com.silastali.app.data.UserItem
import com.silastali.app.databinding.ItemUserBinding
import com.silastali.app.databinding.ItemUserHeaderBinding
import com.silastali.app.ui.RoleNames

class UserAdapter(
    users: List<UserItem>,
    private val onEdit: ((UserItem) -> Unit)? = null,
    private val onDelete: (UserItem) -> Unit,
    private val canDelete: (UserItem) -> Boolean = { true },
    private val showPassword: Boolean = false,
    private val groupByBlock: Boolean = true
) : RecyclerView.Adapter<RecyclerView.ViewHolder>() {

    private sealed class Row {
        class Header(val label: String) : Row()
        class User(val user: UserItem) : Row()
    }

    private val rows: List<Row>

    init {
        rows = if (groupByBlock) buildGrouped(users) else users.map { Row.User(it) }
    }

    private fun buildGrouped(users: List<UserItem>): List<Row> {
        val result = mutableListOf<Row>()
        val order = listOf(
            RoleNames.BLOCK_LASER,
            RoleNames.BLOCK_BENDER,
            RoleNames.BLOCK_FITTER,
            RoleNames.BLOCK_WELDER,
            RoleNames.BLOCK_STOREKEEPER,
            RoleNames.BLOCK_CHIEF,
        )
        val groups = users.groupBy { it.block }
        val keys = order.filter { groups.containsKey(it) } +
            groups.keys.filterNot { it in order }
        for (key in keys) {
            val members = groups.getValue(key)
            if (members.isEmpty()) continue
            result.add(Row.Header(RoleNames.blockDisplayName(key)))
            result.addAll(members.map { Row.User(it) })
        }
        return result
    }

    override fun getItemViewType(position: Int): Int {
        return if (rows[position] is Row.Header) 0 else 1
    }

    override fun onCreateViewHolder(parent: ViewGroup, viewType: Int): RecyclerView.ViewHolder {
        val inflater = LayoutInflater.from(parent.context)
        return if (viewType == 0) {
            HeaderVH(ItemUserHeaderBinding.inflate(inflater, parent, false))
        } else {
            UserVH(ItemUserBinding.inflate(inflater, parent, false))
        }
    }

    override fun onBindViewHolder(holder: RecyclerView.ViewHolder, position: Int) {
        when (val row = rows[position]) {
            is Row.Header -> (holder as HeaderVH).binding.tvHeader.text = row.label
            is Row.User -> bindUser(holder as UserVH, row.user)
        }
    }

    private fun bindUser(holder: UserVH, user: UserItem) {
        holder.binding.apply {
            tvName.text = user.full_name
            tvUsername.text = "@${user.username}"
            tvRole.text = RoleNames.displayName(user.role)
            val block = user.block
            if (!block.isNullOrEmpty()) {
                tvBlock.visibility = View.VISIBLE
                tvBlock.text = "Блок: ${RoleNames.blockDisplayName(block)}"
            } else {
                tvBlock.visibility = View.GONE
            }
            if (showPassword) {
                tvPassword.visibility = View.VISIBLE
                tvPassword.text = if (!user.password_plain.isNullOrEmpty()) "Пароль: ${user.password_plain}" else "Пароль: —"
            } else {
                tvPassword.visibility = View.GONE
            }
            btnDelete.setOnClickListener { onDelete(user) }
            btnDelete.visibility = if (canDelete(user)) View.VISIBLE else View.GONE
            if (onEdit != null) {
                btnEdit.visibility = View.VISIBLE
                btnEdit.setOnClickListener { onEdit!!.invoke(user) }
            } else {
                btnEdit.visibility = View.GONE
            }
        }
    }

    override fun getItemCount() = rows.size

    class HeaderVH(val binding: ItemUserHeaderBinding) : RecyclerView.ViewHolder(binding.root)
    class UserVH(val binding: ItemUserBinding) : RecyclerView.ViewHolder(binding.root)
}