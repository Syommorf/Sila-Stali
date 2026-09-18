package com.silastali.app.ui

import android.content.Context
import android.view.View
import android.widget.RadioButton
import android.widget.RadioGroup

class BlockRolePicker(
    context: Context,
    private val blocks: List<Pair<String, String>>,
    initialBlock: String?,
    initialRole: String?,
) {
    val blockRadio = RadioGroup(context)
    val roleRadio = RadioGroup(context)
    private val blockIds = mutableListOf<Int>()
    private val roleIds = mutableListOf<Int>()
    private var roleValues: List<Pair<String, String>> = listOf()

    init {
        val current = blocks.firstOrNull { it.first == initialBlock }?.first ?: RoleNames.BLOCK_BENDER
        blocks.forEachIndexed { _, (block, display) ->
            val rb = RadioButton(context).apply {
                id = View.generateViewId()
                text = display
                textSize = 15f
                setPadding(48, 20, 48, 20)
                isChecked = block == current
            }
            blockIds.add(rb.id)
            blockRadio.addView(rb)
        }
        rebuildRoles(current, initialRole)
        blockRadio.setOnCheckedChangeListener { _, checkedId ->
            if (checkedId == -1) return@setOnCheckedChangeListener
            val i = blockIds.indexOf(checkedId)
            if (i in 0 until blocks.size) rebuildRoles(blocks[i].first, null)
        }
    }

    private fun rebuildRoles(block: String?, selectedRole: String?) {
        roleRadio.removeAllViews()
        roleIds.clear()
        roleValues = RoleNames.rolesForBlock(block)
        roleValues.forEach { (role, display) ->
            val rb = RadioButton(roleRadio.context).apply {
                id = View.generateViewId()
                text = display
                textSize = 15f
                setPadding(48, 20, 48, 20)
                isChecked = role == selectedRole
            }
            roleIds.add(rb.id)
            roleRadio.addView(rb)
        }
        if (selectedRole == null && roleIds.isNotEmpty()) {
            roleRadio.check(roleIds[0])
        }
    }

    fun selectedBlock(): String {
        val i = blockIds.indexOf(blockRadio.checkedRadioButtonId)
        return blocks[if (i in 0 until blocks.size) i else 0].first
    }

    fun selectedRole(): String {
        val i = roleIds.indexOf(roleRadio.checkedRadioButtonId)
        if (i in 0 until roleValues.size) return roleValues[i].first
        return roleValues.firstOrNull()?.first ?: RoleNames.BENDER
    }
}