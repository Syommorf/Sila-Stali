package com.silastali.app.ui

import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

object ChatTime {
    private val parser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.US)
    private val timeFmt = SimpleDateFormat("HH:mm", Locale.US)
    private val dateTimeFmt = SimpleDateFormat("dd.MM HH:mm", Locale.US)

    fun formatTime(iso: String?): String {
        if (iso.isNullOrEmpty()) return ""
        return try {
            val date = parser.parse(iso) ?: return ""
            val now = Calendar.getInstance()
            val msg = Calendar.getInstance().apply { time = date }
            val sameDay = now.get(Calendar.YEAR) == msg.get(Calendar.YEAR) &&
                now.get(Calendar.DAY_OF_YEAR) == msg.get(Calendar.DAY_OF_YEAR)
            if (sameDay) timeFmt.format(date) else dateTimeFmt.format(date)
        } catch (e: Exception) {
            ""
        }
    }

    fun dateLabel(iso: String?): String {
        if (iso.isNullOrEmpty()) return ""
        return try {
            dateTimeFmt.format(parser.parse(iso) ?: return "")
        } catch (e: Exception) {
            ""
        }
    }
}