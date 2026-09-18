package com.silastali.app.data.network

import android.content.Context
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import com.silastali.app.data.*
import okhttp3.*
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.IOException
import java.util.concurrent.TimeUnit

class ApiClient(private val context: Context) {
    private val gson = Gson()
    private val JSON = "application/json; charset=utf-8".toMediaType()

    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .writeTimeout(300, TimeUnit.SECONDS)
        .dns(DirectFirstDns)
        .addInterceptor(CertInterceptor(context))
        .build()

    var baseUrl = "https://silastali.su"
    var token: String? = null

    private fun authGet(url: String): String {
        val request = Request.Builder()
            .url("$baseUrl$url")
            .addHeader("Authorization", "Bearer $token")
            .get()
            .build()
        val response = client.newCall(request).execute()
        if (!response.isSuccessful) throw IOException("HTTP ${response.code}")
        return response.body?.string() ?: ""
    }

    private fun authPost(url: String, body: Any): String {
        val json = gson.toJson(body)
        val request = Request.Builder()
            .url("$baseUrl$url")
            .addHeader("Authorization", "Bearer $token")
            .post(json.toRequestBody(JSON))
            .build()
        val response = client.newCall(request).execute()
        val text = response.body?.string() ?: ""
        if (!response.isSuccessful) throw IOException("HTTP ${response.code}: $text")
        return text
    }

    private fun authPut(url: String, body: Any): String {
        val json = gson.toJson(body)
        val request = Request.Builder()
            .url("$baseUrl$url")
            .addHeader("Authorization", "Bearer $token")
            .put(json.toRequestBody(JSON))
            .build()
        val response = client.newCall(request).execute()
        val text = response.body?.string() ?: ""
        if (!response.isSuccessful) throw IOException("HTTP ${response.code}: $text")
        return text
    }

    private fun authDelete(url: String): String {
        val request = Request.Builder()
            .url("$baseUrl$url")
            .addHeader("Authorization", "Bearer $token")
            .delete()
            .build()
        val response = client.newCall(request).execute()
        val text = response.body?.string() ?: ""
        if (!response.isSuccessful) throw IOException("HTTP ${response.code}: $text")
        return text
    }

    private fun post(url: String, body: Any): String {
        val json = gson.toJson(body)
        val request = Request.Builder()
            .url("$baseUrl$url")
            .post(json.toRequestBody(JSON))
            .build()
        val response = client.newCall(request).execute()
        val text = response.body?.string() ?: ""
        if (!response.isSuccessful) throw IOException("HTTP ${response.code}: $text")
        return text
    }

    fun login(username: String, password: String): LoginResponse {
        val formBody = FormBody.Builder()
            .add("username", username)
            .add("password", password)
            .build()
        val request = Request.Builder()
            .url("$baseUrl/auth/login")
            .post(formBody)
            .build()
        val response = client.newCall(request).execute()
        val text = response.body?.string() ?: ""
        if (!response.isSuccessful) throw IOException("HTTP ${response.code}: $text")
        return gson.fromJson(text, LoginResponse::class.java)
    }

    fun loginChief(password: String): LoginResponse {
        val formBody = FormBody.Builder()
            .add("password", password)
            .build()
        val request = Request.Builder()
            .url("$baseUrl/auth/login-chief")
            .post(formBody)
            .build()
        val response = client.newCall(request).execute()
        val text = response.body?.string() ?: ""
        if (!response.isSuccessful) throw IOException("HTTP ${response.code}: $text")
        return gson.fromJson(text, LoginResponse::class.java)
    }

    fun getUpdateInfo(): UpdateInfo {
        val request = Request.Builder()
            .url("$baseUrl/app/update")
            .get()
            .build()
        val response = client.newCall(request).execute()
        val text = response.body?.string() ?: ""
        if (!response.isSuccessful) throw IOException("HTTP ${response.code}: $text")
        return gson.fromJson(text, UpdateInfo::class.java)
    }

    fun getEmployees(block: String? = null): List<EmployeeItem> {
        var url = "$baseUrl/auth/employees"
        if (!block.isNullOrEmpty()) url += "?block=$block"
        val request = Request.Builder()
            .url(url)
            .get()
            .build()
        val response = client.newCall(request).execute()
        val text = response.body?.string() ?: ""
        if (!response.isSuccessful) throw IOException("HTTP ${response.code}: $text")
        val type = object : TypeToken<List<EmployeeItem>>() {}.type
        return gson.fromJson(text, type)
    }

    fun getWorks(dateFrom: String? = null, dateTo: String? = null, workerId: Int? = null, partNumber: String? = null): List<WorkItem> {
        var url = "/works?"
        if (dateFrom != null) url += "date_from=$dateFrom&"
        if (dateTo != null) url += "date_to=$dateTo&"
        if (workerId != null) url += "worker_id=$workerId&"
        if (partNumber != null) url += "part_number=$partNumber&"
        val text = authGet(url)
        val type = object : TypeToken<List<WorkItem>>() {}.type
        return gson.fromJson(text, type)
    }

    fun getMyWorks(): List<WorkItem> {
        val text = authGet("/works/my")
        val type = object : TypeToken<List<WorkItem>>() {}.type
        return gson.fromJson(text, type)
    }

    fun createWork(work: WorkCreateRequest): String {
        return authPost("/works", work)
    }

    fun deleteWork(workId: Int): String {
        return authDelete("/works/$workId")
    }

    fun syncWorks(works: List<WorkCreateRequest>): String {
        return authPost("/works/sync", SyncRequest(works))
    }

    fun getStatsOverview(dateFrom: String? = null, dateTo: String? = null): OverviewStat {
        var url = "/stats/overview?"
        if (dateFrom != null) url += "date_from=$dateFrom&"
        if (dateTo != null) url += "date_to=$dateTo&"
        val text = authGet(url)
        return gson.fromJson(text, OverviewStat::class.java)
    }

    fun getStatsByWorker(dateFrom: String? = null, dateTo: String? = null): List<WorkerStat> {
        var url = "/stats/by-worker?"
        if (dateFrom != null) url += "date_from=$dateFrom&"
        if (dateTo != null) url += "date_to=$dateTo&"
        val text = authGet(url)
        val type = object : TypeToken<List<WorkerStat>>() {}.type
        return gson.fromJson(text, type)
    }

    fun getStatsTimeline(groupBy: String, dateFrom: String? = null, dateTo: String? = null): List<TimelinePeriod> {
        var url = "/stats/timeline?group_by=$groupBy&"
        if (dateFrom != null) url += "date_from=$dateFrom&"
        if (dateTo != null) url += "date_to=$dateTo&"
        val text = authGet(url)
        val type = object : TypeToken<List<TimelinePeriod>>() {}.type
        return gson.fromJson(text, type)
    }

    fun getMyStats(dateFrom: String? = null, dateTo: String? = null, groupBy: String = "day"): MyStats {
        var url = "/stats/my?group_by=$groupBy&"
        if (dateFrom != null) url += "date_from=$dateFrom&"
        if (dateTo != null) url += "date_to=$dateTo&"
        val text = authGet(url)
        return gson.fromJson(text, MyStats::class.java)
    }

    fun updateMe(currentPassword: String, newUsername: String? = null, newPassword: String? = null): String {
        return authPut("/users/me", UserMeUpdateRequest(currentPassword, newUsername, newPassword))
    }

    fun getUsers(): List<UserItem> {
        val text = authGet("/users")
        val type = object : TypeToken<List<UserItem>>() {}.type
        return gson.fromJson(text, type)
    }

    fun createUser(user: UserCreateRequest): String {
        return authPost("/users", user)
    }

    fun updateUser(userId: Int, data: UserUpdateRequest): String {
        return authPut("/users/$userId", data)
    }

    fun deleteUser(userId: Int): String {
        return authDelete("/users/$userId")
    }

    fun getExportUrl(dateFrom: String? = null, dateTo: String? = null, workerId: Int? = null): String {
        var url = "$baseUrl/export/excel?"
        if (dateFrom != null) url += "date_from=$dateFrom&"
        if (dateTo != null) url += "date_to=$dateTo&"
        if (workerId != null) url += "worker_id=$workerId&"
        return url
    }

    fun getOrders(status: String? = null, block: String? = null): List<SpecOrder> {
        var url = "/orders"
        val params = mutableListOf<String>()
        if (status != null) params += "status=$status"
        if (block != null) params += "block=$block"
        if (params.isNotEmpty()) url += "?" + params.joinToString("&")
        val text = authGet(url)
        val type = object : TypeToken<List<SpecOrder>>() {}.type
        return gson.fromJson(text, type)
    }

    fun markOrderReady(orderId: Int): String {
        return authPost("/orders/$orderId/ready", mapOf<String, Any>())
    }

    fun deleteOrder(orderId: Int): String {
        return authDelete("/orders/$orderId")
    }

    fun getOrderDetail(orderId: Int): OrderDetail {
        val text = authGet("/orders/$orderId")
        return gson.fromJson(text, OrderDetail::class.java)
    }

    fun uploadOrderSpec(fileName: String, bytes: ByteArray): UploadOrdersResult {
        var lastError: Exception? = null
        val maxAttempts = 3
        for (attempt in 1..maxAttempts) {
            try {
                return performUpload(fileName, bytes)
            } catch (e: Exception) {
                lastError = e
                val retryable = e is IOException && !e.message.orEmpty().startsWith("HTTP ")
                if (retryable && attempt < maxAttempts) {
                    try {
                        Thread.sleep(2000L * attempt)
                    } catch (_: InterruptedException) {
                        break
                    }
                } else {
                    break
                }
            }
        }
        throw lastError ?: IOException("Ошибка загрузки")
    }

    private fun performUpload(fileName: String, bytes: ByteArray): UploadOrdersResult {
        val body = MultipartBody.Builder()
            .setType(MultipartBody.FORM)
            .addFormDataPart("file", fileName, bytes.toRequestBody("application/octet-stream".toMediaType()))
            .build()
        val request = Request.Builder()
            .url("$baseUrl/orders/upload")
            .addHeader("Authorization", "Bearer $token")
            .post(body)
            .build()
        val response = client.newCall(request).execute()
        val text = response.body?.string() ?: ""
        if (!response.isSuccessful) throw IOException("HTTP ${response.code}: $text")
        return gson.fromJson(text, UploadOrdersResult::class.java)
    }

    fun completeOrderItem(orderId: Int, itemId: Int, quantity: Int, executorId: Int? = null, note: String? = null, stage: String? = null): String {
        val body = mutableMapOf<String, Any>("quantity" to quantity)
        if (executorId != null) body["executor_id"] = executorId
        if (!note.isNullOrEmpty()) body["note"] = note
        if (!stage.isNullOrEmpty()) body["stage"] = stage
        return authPost("/orders/$orderId/items/$itemId/complete", body)
    }

    fun deleteOrderCompletion(completionId: Int): String {
        return authDelete("/orders/completions/$completionId")
    }

    fun closeOrder(orderId: Int): String {
        val request = Request.Builder()
            .url("$baseUrl/orders/$orderId/close")
            .addHeader("Authorization", "Bearer $token")
            .post("".toRequestBody(null))
            .build()
        val response = client.newCall(request).execute()
        val text = response.body?.string() ?: ""
        if (!response.isSuccessful) throw IOException("HTTP ${response.code}: $text")
        return text
    }

    fun claimOrderItem(orderId: Int, itemId: Int, executorId: Int? = null): String {
        val body = mutableMapOf<String, Any>()
        if (executorId != null) body["executor_id"] = executorId
        return authPost("/orders/$orderId/items/$itemId/claim", body)
    }

    fun releaseOrderItem(orderId: Int, itemId: Int): String {
        return authDelete("/orders/$orderId/items/$itemId/claim")
    }

    fun addClaimParticipant(orderId: Int, itemId: Int, workerId: Int): OrderClaim {
        val text = authPost(
            "/orders/$orderId/items/$itemId/claim/participants",
            mapOf("executor_id" to workerId)
        )
        return gson.fromJson(text, OrderClaim::class.java)
    }

    fun removeClaimParticipant(orderId: Int, itemId: Int, workerId: Int): OrderClaim {
        val text = authDelete("/orders/$orderId/items/$itemId/claim/participants/$workerId")
        return gson.fromJson(text, OrderClaim::class.java)
    }

    fun getOrderStats(dateFrom: String? = null, dateTo: String? = null): List<OrderStatsRow> {
        var url = "/orders/stats/list?"
        if (dateFrom != null) url += "date_from=$dateFrom&"
        if (dateTo != null) url += "date_to=$dateTo&"
        val text = authGet(url)
        val type = object : TypeToken<List<OrderStatsRow>>() {}.type
        return gson.fromJson(text, type)
    }

    fun getMyOrderStats(dateFrom: String? = null, dateTo: String? = null): OrderStatsRow {
        var url = "/orders/stats/my?"
        if (dateFrom != null) url += "date_from=$dateFrom&"
        if (dateTo != null) url += "date_to=$dateTo&"
        val text = authGet(url)
        return gson.fromJson(text, OrderStatsRow::class.java)
    }

    fun getCrewInvites(): List<CrewInvite> {
        val text = authGet("/crew-invites")
        val type = object : TypeToken<List<CrewInvite>>() {}.type
        return gson.fromJson(text, type)
    }

    fun respondCrewInvite(inviteId: Int, accept: Boolean): String {
        return authPost("/crew-invites/$inviteId/respond", mapOf("accept" to accept))
    }

    fun getChats(): List<ChatItem> {
        val text = authGet("/chat/list")
        val type = object : TypeToken<List<ChatItem>>() {}.type
        return gson.fromJson(text, type)
    }

    fun getChatMessages(chatId: Int, afterId: Int = 0, limit: Int = 200): ChatMessagesResponse {
        val text = authGet("/chat/$chatId/messages?after_id=$afterId&limit=$limit")
        return gson.fromJson(text, ChatMessagesResponse::class.java)
    }

    fun sendChatMessage(chatId: Int, text: String): ChatMessage {
        val r = authPost("/chat/$chatId/messages", SendMessageRequest(text))
        return gson.fromJson(r, ChatMessage::class.java)
    }

    fun createDm(userId: Int): ChatItem {
        val r = authPost("/chat/dm", DmRequest(userId))
        return gson.fromJson(r, ChatItem::class.java)
    }

    fun createChat(name: String, memberIds: List<Int>): ChatItem {
        val r = authPost("/chat/create", CreateChatRequest(name, memberIds))
        return gson.fromJson(r, ChatItem::class.java)
    }

    fun markChatRead(chatId: Int, lastMessageId: Int): String {
        return authPost("/chat/$chatId/read", ReadRequest(lastMessageId))
    }

    fun addChatMembers(chatId: Int, userIds: List<Int>): String {
        return authPost("/chat/$chatId/members", AddMembersRequest(userIds))
    }

    fun leaveChat(chatId: Int): String {
        return authDelete("/chat/$chatId/members/me")
    }

    fun deleteChat(chatId: Int): String {
        return authDelete("/chat/$chatId")
    }
}
