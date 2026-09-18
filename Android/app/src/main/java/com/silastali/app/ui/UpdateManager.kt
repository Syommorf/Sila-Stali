package com.silastali.app.ui

import android.app.Activity
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.os.Environment
import android.provider.Settings
import android.widget.ProgressBar
import android.widget.Toast
import androidx.appcompat.app.AlertDialog
import androidx.core.content.FileProvider
import com.silastali.app.data.UpdateInfo
import com.silastali.app.data.network.ApiClient
import com.silastali.app.data.network.DirectFirstDns
import kotlinx.coroutines.*
import okhttp3.OkHttpClient
import okhttp3.Request
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.TimeUnit

class UpdateManager(
    private val activity: Activity,
    private val apiClient: ApiClient,
    private val onInstallPermissionRequested: () -> Unit = {}
) {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val http = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(120, TimeUnit.SECONDS)
        .writeTimeout(120, TimeUnit.SECONDS)
        .dns(DirectFirstDns)
        .build()

    fun checkAndPrompt(onDismiss: () -> Unit) {
        scope.launch {
            try {
                val info = apiClient.getUpdateInfo()
                if (info.available && info.version_code > currentVersionCode()) {
                    withContext(Dispatchers.Main) {
                        showUpdateDialog(info, onDismiss)
                    }
                } else {
                    withContext(Dispatchers.Main) { onDismiss() }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) { onDismiss() }
            }
        }
    }

    private fun currentVersionCode(): Int {
        return try {
            activity.packageManager.getPackageInfo(activity.packageName, 0).versionCode
        } catch (e: Exception) {
            0
        }
    }

    private fun showUpdateDialog(info: UpdateInfo, onDismiss: () -> Unit) {
        if (activity.isFinishing) {
            onDismiss()
            return
        }
        val dialog = AlertDialog.Builder(activity)
            .setTitle("Доступно обновление ${info.version}")
            .setMessage("Установлена более старая версия. Обновить приложение сейчас?")
            .setPositiveButton("Обновить") { _, _ -> downloadAndInstall(info, onDismiss) }
            .setNegativeButton("Позже") { _, _ -> onDismiss() }
            .setCancelable(false)
            .create()
        dialog.setOnDismissListener { onDismiss() }
        dialog.show()
    }

    private fun downloadAndInstall(info: UpdateInfo, onDismiss: () -> Unit) {
        if (Build.VERSION.SDK_INT >= 26 && !activity.packageManager.canRequestPackageInstalls()) {
            AlertDialog.Builder(activity)
                .setTitle("Разрешите установку приложений")
                .setMessage("Для обновления приложения разрешите установку из источника «Сила Стали». Сейчас откроются настройки — включите там переключатель и вернитесь в приложение.")
                .setPositiveButton("Открыть настройки") { _, _ ->
                    onInstallPermissionRequested()
                    try {
                        val intent = Intent(
                            Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES,
                            Uri.parse("package:${activity.packageName}")
                        )
                        activity.startActivity(intent)
                    } catch (e: Exception) {
                        try {
                            activity.startActivity(Intent(Settings.ACTION_SETTINGS))
                        } catch (_: Exception) {
                        }
                    }
                    onDismiss()
                }
                .setNegativeButton("Позже") { _, _ -> onDismiss() }
                .setCancelable(false)
                .show()
            return
        }

        val url = info.apk_url ?: run {
            onDismiss()
            return
        }
        val progress = AlertDialog.Builder(activity)
            .setTitle("Скачивание обновления")
            .setMessage(info.version)
            .setView(ProgressBar(activity))
            .setCancelable(false)
            .create()
        progress.show()

        scope.launch {
            try {
                val file = download(url)
                withContext(Dispatchers.Main) {
                    progress.dismiss()
                    try {
                        installApk(file)
                    } catch (e: Exception) {
                        Toast.makeText(activity, "Не удалось запустить установку: ${e.message}", Toast.LENGTH_LONG).show()
                    }
                    onDismiss()
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    progress.dismiss()
                    showDownloadErrorDialog(info, onDismiss)
                }
            }
        }
    }

    private fun showDownloadErrorDialog(info: UpdateInfo, onDismiss: () -> Unit) {
        if (activity.isFinishing) {
            onDismiss()
            return
        }
        AlertDialog.Builder(activity)
            .setTitle("Не удалось скачать обновление")
            .setMessage("Проверьте интернет-соединение и попробуйте ещё раз.")
            .setPositiveButton("Повторить") { _, _ -> downloadAndInstall(info, onDismiss) }
            .setNegativeButton("Позже") { _, _ -> onDismiss() }
            .setCancelable(false)
            .show()
    }

    private suspend fun download(url: String): File {
        return withContext(Dispatchers.IO) {
            val request = Request.Builder().url(url).get().build()
            val response = http.newCall(request).execute()
            if (!response.isSuccessful) throw java.io.IOException("HTTP ${response.code}")
            val dir = File(activity.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS), "updates")
            if (!dir.exists()) dir.mkdirs()
            val file = File(dir, "sila-stali.apk")
            if (file.exists()) file.delete()
            val body = response.body ?: throw java.io.IOException("Пустой ответ")
            FileOutputStream(file).use { out ->
                body.byteStream().copyTo(out)
            }
            file
        }
    }

    private fun installApk(file: File) {
        val uri = FileProvider.getUriForFile(activity, "${activity.packageName}.fileprovider", file)
        val intent = Intent(Intent.ACTION_VIEW).apply {
            setDataAndType(uri, "application/vnd.android.package-archive")
            addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        }
        activity.startActivity(intent)
    }
}