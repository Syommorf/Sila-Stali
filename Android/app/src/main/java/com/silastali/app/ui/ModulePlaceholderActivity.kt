package com.silastali.app.ui

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import com.silastali.app.databinding.ActivityModulePlaceholderBinding

class ModulePlaceholderActivity : AppCompatActivity() {
    private lateinit var binding: ActivityModulePlaceholderBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityModulePlaceholderBinding.inflate(layoutInflater)
        setContentView(binding.root)

        val name = intent.getStringExtra("module_name") ?: ""
        val imageRes = intent.getIntExtra("module_image", 0)

        binding.tvModuleTitle.text = "«$name»"
        if (imageRes != 0) binding.imgModuleBg.setImageResource(imageRes)
        binding.btnModuleBack.setOnClickListener { finish() }
    }
}