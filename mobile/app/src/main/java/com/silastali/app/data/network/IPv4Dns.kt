package com.silastali.app.data.network

import okhttp3.Dns
import java.net.Inet4Address
import java.net.InetAddress

object IPv4Dns : Dns {
    override fun lookup(hostname: String): List<InetAddress> {
        val all = try {
            InetAddress.getAllByName(hostname).toList()
        } catch (e: Exception) {
            emptyList()
        }
        val v4 = all.filter { it is Inet4Address }
        return if (v4.isNotEmpty()) v4 else all
    }
}