package com.silastali.app.ui

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.silastali.app.databinding.ActivityStaffMenuBinding

class StaffMenuActivity : AppCompatActivity() {
    private lateinit var binding: ActivityStaffMenuBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityStaffMenuBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.btnLaser.setOnClickListener { openBlock(RoleNames.BLOCK_LASER) }
        binding.btnBender.setOnClickListener { openBlock(RoleNames.BLOCK_BENDER) }
        binding.btnFitter.setOnClickListener { openBlock(RoleNames.BLOCK_FITTER) }
        binding.btnWelder.setOnClickListener { openBlock(RoleNames.BLOCK_WELDER) }
        binding.btnStorekeeper.setOnClickListener { openBlock(RoleNames.BLOCK_STOREKEEPER) }
    }

    private fun openBlock(block: String) {
        startActivity(Intent(this, UsersActivity::class.java).putExtra("block", block))
    }
}