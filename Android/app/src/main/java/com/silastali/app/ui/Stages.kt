package com.silastali.app.ui

object Stages {
    const val LASER = "laser"
    const val BENDER = "bender"
    const val WELDER = "welder"
    const val FITTER = "fitter"
    const val STOREKEEPER = "storekeeper"

    val PROD_ORDER = listOf(LASER, BENDER, WELDER, FITTER)

    val BLOCK_NAME = mapOf(
        LASER to "Лазер",
        BENDER to "Гибка",
        FITTER to "Мех. обработка",
        WELDER to "Сварка",
        STOREKEEPER to "Склад",
    )

    fun name(code: String?): String = BLOCK_NAME[code] ?: (code ?: "")
}