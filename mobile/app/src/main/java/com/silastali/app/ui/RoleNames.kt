package com.silastali.app.ui

object RoleNames {
    const val ADMIN = "admin"
    const val MANAGER = "manager"
    const val APPRENTICE = "apprentice"
    const val BENDER = "bender"
    const val SENIOR_BENDER = "senior_bender"
    const val LASER_CUTTER = "laser_cutter"
    const val FITTER = "fitter"
    const val WELDER = "welder"
    const val STOREKEEPER = "storekeeper"

    val WORKER_ROLES = listOf(APPRENTICE, BENDER, SENIOR_BENDER, LASER_CUTTER, FITTER, WELDER, STOREKEEPER)

    const val BLOCK_LASER = "laser"
    const val BLOCK_BENDER = "bender"
    const val BLOCK_FITTER = "fitter"
    const val BLOCK_WELDER = "welder"
    const val BLOCK_STOREKEEPER = "storekeeper"
    const val BLOCK_CHIEF = "chief"

    val workerBlocks = listOf(
        BLOCK_LASER to "Лазерщики",
        BLOCK_BENDER to "Гибщики",
        BLOCK_FITTER to "Слесаря",
        BLOCK_WELDER to "Сварщики",
        BLOCK_STOREKEEPER to "Кладовщики",
    )

    val allBlocks = workerBlocks + (BLOCK_CHIEF to "Руководство")

    fun blockDisplayName(block: String?): String {
        return when (block) {
            BLOCK_LASER -> "Лазерщики"
            BLOCK_BENDER -> "Гибщики"
            BLOCK_FITTER -> "Слесаря"
            BLOCK_WELDER -> "Сварщики"
            BLOCK_STOREKEEPER -> "Кладовщики"
            BLOCK_CHIEF -> "Руководство"
            else -> "Без блока"
        }
    }

    fun displayName(role: String?): String {
        return when (role) {
            ADMIN -> "Администратор"
            MANAGER -> "Начальник"
            APPRENTICE -> "Ученик гибщика"
            BENDER -> "Гибщик"
            SENIOR_BENDER -> "Старший гибщик"
            LASER_CUTTER -> "Лазерщик"
            FITTER -> "Слесарь"
            WELDER -> "Сварщик"
            STOREKEEPER -> "Кладовщик"
            else -> role ?: "Гибщик"
        }
    }

    /** Должности внутри блока. У «Гибщики» их несколько, у остальных — пока базовая. */
    fun rolesForBlock(block: String?): List<Pair<String, String>> {
        return when (block) {
            BLOCK_BENDER -> listOf(
                APPRENTICE to "Ученик гибщика",
                BENDER to "Гибщик",
                SENIOR_BENDER to "Старший гибщик",
            )
            BLOCK_LASER -> listOf(LASER_CUTTER to "Лазерщик")
            BLOCK_FITTER -> listOf(FITTER to "Слесарь")
            BLOCK_WELDER -> listOf(WELDER to "Сварщик")
            BLOCK_STOREKEEPER -> listOf(STOREKEEPER to "Кладовщик")
            BLOCK_CHIEF -> listOf(MANAGER to "Начальник")
            else -> listOf(BENDER to "Гибщик")
        }
    }
}