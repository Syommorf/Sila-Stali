package com.silastali.app.ui

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.silastali.app.databinding.ActivityWorkMenuBinding

class WorkMenuActivity : AppCompatActivity() {
    private lateinit var binding: ActivityWorkMenuBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityWorkMenuBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)
        supportActionBar?.setDisplayHomeAsUpEnabled(true)
        binding.toolbar.setNavigationOnClickListener { finish() }

        binding.btnUploadOrder.setOnClickListener {
            startActivity(Intent(this, UploadOrderActivity::class.java))
        }

        binding.btnViewOrders.setOnClickListener {
            startActivity(Intent(this, OrderListActivity::class.java))
        }

        binding.btnStats.setOnClickListener {
            startActivity(Intent(this, StatsActivity::class.java))
        }

        binding.btnBack.setOnClickListener { finish() }
    }
}