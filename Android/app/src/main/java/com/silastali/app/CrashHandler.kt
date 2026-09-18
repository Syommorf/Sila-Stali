package com.silastali.app

import android.content.Context
import java.io.File
import java.io.PrintWriter
import java.io.StringWriter

class CrashHandler(private val context: Context) : Thread.UncaughtExceptionHandler {
    private val defaultHandler = Thread.getDefaultUncaughtExceptionHandler()

    override fun uncaughtException(thread: Thread, throwable: Throwable) {
        try {
            val sw = StringWriter()
            throwable.printStackTrace(PrintWriter(sw))
            val file = File(context.filesDir, "crash.log")
            file.writeText("${sw.toString()}\n\nTime: ${System.currentTimeMillis()}\n")
        } catch (_: Exception) {
        }
        defaultHandler?.uncaughtException(thread, throwable)
    }
}