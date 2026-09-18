package com.silastali.app.data

data class LoginRequest(val username: String, val password: String)

data class LoginResponse(
    val access_token: String,
    val token_type: String,
    val user_id: Int,
    val full_name: String,
    val role: String,
    val block: String? = null
)

data class EmployeeItem(
    val id: Int = 0,
    val full_name: String = "",
    val username: String = "",
    val role: String = ""
)

data class WorkItem(
    val id: Int = 0,
    val worker_id: Int = 0,
    val worker_name: String? = null,
    val part_number: String? = null,
    val quantity: Int? = null,
    val note: String? = null,
    val start_time: String? = null,
    val end_time: String? = null,
    val duration_minutes: Double? = null
)

data class WorkCreateRequest(
    val part_number: String,
    val quantity: Int,
    val note: String,
    val start_time: String,
    val end_time: String? = null
)

data class SyncRequest(val works: List<WorkCreateRequest>)

data class OverviewStat(
    val total_quantity: Int,
    val total_works: Int,
    val total_workers: Int,
    val avg_duration_minutes: Double?
)

data class WorkerStat(
    val worker_id: Int,
    val worker_name: String,
    val total_quantity: Int,
    val total_works: Int,
    val avg_duration_minutes: Double?,
    val parts_breakdown: Map<String, Int>
)

data class UserItem(
    val id: Int = 0,
    val username: String = "",
    val full_name: String = "",
    val role: String = "worker",
    val password_plain: String? = null,
    val block: String? = null
)

data class UserCreateRequest(
    val username: String,
    val password: String,
    val full_name: String,
    val role: String = "worker",
    val block: String? = null
)

data class UserUpdateRequest(
    val full_name: String? = null,
    val role: String? = null,
    val password: String? = null,
    val username: String? = null,
    val block: String? = null
)

data class UserMeUpdateRequest(
    val current_password: String,
    val new_username: String? = null,
    val new_password: String? = null
)

data class MyStats(
    val total_quantity: Int = 0,
    val total_works: Int = 0,
    val avg_duration_minutes: Double? = null,
    val periods: List<TimelinePeriod> = emptyList()
)

data class UpdateInfo(
    val available: Boolean = false,
    val version: String? = null,
    val version_code: Int = 0,
    val apk_size: Long = 0,
    val apk_url: String? = null
)

data class TimelinePeriod(
    val period: String = "",
    val total_quantity: Int = 0,
    val total_works: Int = 0
)

data class StageCount(
    val total: Int = 0,
    val done: Int = 0
)

data class ItemStage(
    val total: Int = 0,
    val done: Int = 0,
    val full: Boolean = false
)

data class SpecOrder(
    val order_id: Int = 0,
    val order_number: String = "",
    val name: String = "",
    val status: String = "open",
    val created_at: String = "",
    val ready_at: String? = null,
    val total_items: Int = 0,
    val bending_items: Int = 0,
    val total_bend_quantity: Int = 0,
    val done_bend_quantity: Int = 0,
    val remaining_bend_quantity: Int = 0,
    val percent: Int = 0,
    val blocks: List<String> = emptyList(),
    val stages: Map<String, StageCount> = emptyMap()
)

data class OrderCompletion(
    val id: Int = 0,
    val executor_id: Int = 0,
    val executor_name: String = "",
    val marked_by: Int = 0,
    val marked_by_name: String = "",
    val quantity: Int = 0,
    val note: String = "",
    val stage: String = "",
    val completed_at: String = ""
)

data class ClaimWorker(val id: Int = 0, val name: String = "")

data class OrderClaim(
    val id: Int = 0,
    val worker_id: Int = 0,
    val worker_name: String = "",
    val claimed_at: String = "",
    val completed_at: String? = null,
    val workers: List<ClaimWorker>? = null,
    val pending: List<ClaimWorker>? = null
)

data class OrderItemDetail(
    val id: Int = 0,
    val part_number: String = "",
    val quantity: Int = 0,
    val thickness: Double? = null,
    val steel_grade: String = "",
    val route: String = "",
    val needs_bending: Boolean = false,
    val done_quantity: Int = 0,
    val remaining: Int = 0,
    val stages: Map<String, ItemStage> = emptyMap(),
    val untracked_route: Boolean = false,
    val completions: List<OrderCompletion> = emptyList(),
    val claim: OrderClaim? = null,
    val active: Boolean = true,
    val stage_done: Boolean = false
)

data class OrderDetail(
    val order_id: Int = 0,
    val order_number: String = "",
    val name: String = "",
    val status: String = "open",
    val created_at: String = "",
    val items: List<OrderItemDetail> = emptyList()
)

data class OrderStatsRow(
    val worker_id: Int = 0,
    val worker_name: String = "",
    val total_bent_quantity: Int = 0,
    val marks: Int = 0,
    val distinct_parts: Int = 0
)

data class UploadOrderEntry(
    val order_id: Int = 0,
    val order_number: String = "",
    val name: String = "",
    val items: Int = 0,
    val bending_items: Int = 0,
    val status: String = ""
)

data class UploadOrdersResult(
    val orders: List<UploadOrderEntry> = emptyList()
)

data class CrewInvite(
    val id: Int = 0,
    val claim_id: Int = 0,
    val item_id: Int = 0,
    val part_number: String = "",
    val order_id: Int = 0,
    val order_number: String = "",
    val quantity: Int = 0,
    val inviter_name: String = "",
    val worker_id: Int = 0,
    val invited_at: String = ""
)

data class ChatItem(
    val id: Int,
    val type: String,
    val name: String?,
    val block: String?,
    val created_at: String?,
    val member_count: Int,
    val unread_count: Int,
    val last_message: ChatMessage?,
    val other_user_id: Int?,
    val other_user_name: String?
)

data class ChatMessage(
    val id: Int,
    val chat_id: Int,
    val sender_id: Int,
    val sender_name: String?,
    val sender_block: String?,
    val text: String,
    val created_at: String?,
    val edited_at: String?,
    val deleted: Boolean
)

data class CreateChatRequest(
    val name: String,
    val member_ids: List<Int>
)

data class DmRequest(
    val user_id: Int
)

data class SendMessageRequest(
    val text: String
)

data class ReadRequest(
    val last_message_id: Int
)

data class AddMembersRequest(
    val user_ids: List<Int>
)

data class ChatMessagesResponse(
    val chat_id: Int,
    val messages: List<ChatMessage>
)
