package com.silastali.app.data.network

import okhttp3.Dns
import java.net.Inet4Address
import java.net.InetAddress

object DirectFirstDns : Dns {
    private const val ORIGIN_IP = "194.87.98.86"

    override fun lookup(hostname: String): List<InetAddress> {
        val all = try {
            InetAddress.getAllByName(hostname).toList()
        } catch (e: Exception) {
            emptyList()
        }
        val v4 = all.filter { it is Inet4Address }
        val result = LinkedHashSet<InetAddress>()
        if (hostname.equals("silastali.su", ignoreCase = true)) {
            try {
                InetAddress.getAllByName(ORIGIN_IP).toList()
                    .filter { it is Inet4Address }
                    .forEach { result.add(it) }
            } catch (e: Exception) {
            }
        }
        result.addAll(if (v4.isNotEmpty()) v4 else all)
        return result.toList()
    }
}