package com.silastali.app.data.network

import android.content.Context
import android.content.pm.PackageManager
import okhttp3.Interceptor
import okhttp3.Response
import java.security.MessageDigest

class CertInterceptor(context: Context) : Interceptor {
    private val certHash: String by lazy { computeHash(context) }

    override fun intercept(chain: Interceptor.Chain): Response {
        val request = chain.request().newBuilder()
            .addHeader("X-APK-Cert", certHash)
            .build()
        return chain.proceed(request)
    }

    private fun computeHash(context: Context): String {
        return try {
            val sig = if (android.os.Build.VERSION.SDK_INT >= 28) {
                val info = context.packageManager.getPackageInfo(
                    context.packageName, PackageManager.GET_SIGNING_CERTIFICATES
                )
                info.signingInfo?.apkContentsSigners?.firstOrNull()
            } else {
                @Suppress("DEPRECATION")
                val info = context.packageManager.getPackageInfo(
                    context.packageName, PackageManager.GET_SIGNATURES
                )
                info.signatures?.firstOrNull()
            }
            val md = MessageDigest.getInstance("SHA-256")
            md.digest(sig!!.toByteArray()).joinToString("") { "%02x".format(it) }
        } catch (_: Exception) {
            ""
        }
    }
}
