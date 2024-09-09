# --------------------------
# PM register fields
# --------------------------

# AHB BUS
CLOCK_AHB_CPU_S = 0
CLOCK_AHB_CPU_M = (1 << CLOCK_AHB_CPU_S)
CLOCK_AHB_EEPROM_S = 1
CLOCK_AHB_EEPROM_M = (1 << CLOCK_AHB_EEPROM_S)
CLOCK_AHB_RAM_S = 2
CLOCK_AHB_RAM_M = (1 << CLOCK_AHB_RAM_S)
CLOCK_AHB_SPIFI_S = 3
CLOCK_AHB_SPIFI_M = (1 << CLOCK_AHB_SPIFI_S)
CLOCK_AHB_TCB_S = 4
CLOCK_AHB_TCB_M = (1 << CLOCK_AHB_TCB_S)
CLOCK_AHB_DMA_S = 5
CLOCK_AHB_DMA_M = (1 << CLOCK_AHB_DMA_S)
CLOCK_AHB_CRYPTO_S = 6
CLOCK_AHB_CRYPTO_M = (1 << CLOCK_AHB_CRYPTO_S)
CLOCK_AHB_CRC32_S = 7
CLOCK_AHB_CRC32_M = (1 << CLOCK_AHB_CRC32_S)

# APB M
CLOCK_APB_M_PM_S = 0
CLOCK_APB_M_PM_M = (1 << CLOCK_APB_M_PM_S)
CLOCK_APB_M_EPIC_S = 1
CLOCK_APB_M_EPIC_M = (1 << CLOCK_APB_M_EPIC_S)
CLOCK_APB_M_TIMER32_0_S = 2
CLOCK_APB_M_TIMER32_0_M = (1 << CLOCK_APB_M_TIMER32_0_S)
CLOCK_APB_M_PAD_CONFIG_S = 3
CLOCK_APB_M_PAD_CONFIG_M = (1 << CLOCK_APB_M_PAD_CONFIG_S)
CLOCK_APB_M_WDT_BUS_S = 4
CLOCK_APB_M_WDT_BUS_M = (1 << CLOCK_APB_M_WDT_BUS_S)
CLOCK_APB_M_OTP_S = 5
CLOCK_APB_M_OTP_M = (1 << CLOCK_APB_M_OTP_S)
CLOCK_APB_M_PMON_S = 6
CLOCK_APB_M_PMON_M = (1 << CLOCK_APB_M_PMON_S)
CLOCK_APB_M_WU_S = 7
CLOCK_APB_M_WU_M = (1 << CLOCK_APB_M_WU_S)
CLOCK_APB_M_RTC_S = 8
CLOCK_APB_M_RTC_M = (1 << CLOCK_APB_M_RTC_S)

# APB_P
CLOCK_APB_P_WDT_S = 0
CLOCK_APB_P_WDT_M = (1 << CLOCK_APB_P_WDT_S)
CLOCK_APB_P_UART_0_S = 1
CLOCK_APB_P_UART_0_M = (1 << CLOCK_APB_P_UART_0_S)
CLOCK_APB_P_UART_1_S = 2
CLOCK_APB_P_UART_1_M = (1 << CLOCK_APB_P_UART_1_S)
CLOCK_APB_P_TIMER16_0_S = 3
CLOCK_APB_P_TIMER16_0_M = (1 << CLOCK_APB_P_TIMER16_0_S)
CLOCK_APB_P_TIMER16_1_S = 4
CLOCK_APB_P_TIMER16_1_M = (1 << CLOCK_APB_P_TIMER16_1_S)
CLOCK_APB_P_TIMER16_2_S = 5
CLOCK_APB_P_TIMER16_2_M = (1 << CLOCK_APB_P_TIMER16_2_S)
CLOCK_APB_P_TIMER32_1_S = 6
CLOCK_APB_P_TIMER32_1_M = (1 << CLOCK_APB_P_TIMER32_1_S)
CLOCK_APB_P_TIMER32_2_S = 7
CLOCK_APB_P_TIMER32_2_M = (1 << CLOCK_APB_P_TIMER32_2_S)
CLOCK_APB_P_SPI_0_S = 8
CLOCK_APB_P_SPI_0_M = (1 << CLOCK_APB_P_SPI_0_S)
CLOCK_APB_P_SPI_1_S = 9
CLOCK_APB_P_SPI_1_M = (1 << CLOCK_APB_P_SPI_1_S)
CLOCK_APB_P_I2C_0_S = 10
CLOCK_APB_P_I2C_0_M = (1 << CLOCK_APB_P_I2C_0_S)
CLOCK_APB_P_I2C_1_S = 11
CLOCK_APB_P_I2C_1_M = (1 << CLOCK_APB_P_I2C_1_S)
CLOCK_APB_P_GPIO_0_S = 12
CLOCK_APB_P_GPIO_0_M = (1 << CLOCK_APB_P_GPIO_0_S)
CLOCK_APB_P_GPIO_1_S = 13
CLOCK_APB_P_GPIO_1_M = (1 << CLOCK_APB_P_GPIO_1_S)
CLOCK_APB_P_GPIO_2_S = 14
CLOCK_APB_P_GPIO_2_M = (1 << CLOCK_APB_P_GPIO_2_S)
CLOCK_APB_P_ANALOG_S = 15
CLOCK_APB_P_ANALOG_M = (1 << CLOCK_APB_P_ANALOG_S)
CLOCK_APB_P_GPIO_IRQ_S = 16
CLOCK_APB_P_GPIO_IRQ_M = (1 << CLOCK_APB_P_GPIO_IRQ_S)