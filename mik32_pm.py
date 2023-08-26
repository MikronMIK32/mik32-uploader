# --------------------------
# PM register offset
# --------------------------
PM_BASE_ADDRESS = 0x000050000

PM_Clk_AHB_Set_OFFSET = 0x0C
PM_Clk_APB_M_Set_OFFSET = 0x14
PM_Clk_APB_P_Set_OFFSET = 0x1C

# --------------------------
# PM register fields
# --------------------------

# AHB BUS
PM_CLOCK_CPU_S = 0
PM_CLOCK_CPU_M = (1 << PM_CLOCK_CPU_S)
PM_CLOCK_EEPROM_S = 1
PM_CLOCK_EEPROM_M = (1 << PM_CLOCK_EEPROM_S)
PM_CLOCK_RAM_S = 2
PM_CLOCK_RAM_M = (1 << PM_CLOCK_RAM_S)
PM_CLOCK_SPIFI_S = 3
PM_CLOCK_SPIFI_M = (1 << PM_CLOCK_SPIFI_S)
PM_CLOCK_TCB_S = 4
PM_CLOCK_TCB_M = (1 << PM_CLOCK_TCB_S)
PM_CLOCK_DMA_S = 5
PM_CLOCK_DMA_M = (1 << PM_CLOCK_DMA_S)
PM_CLOCK_CRYPTO_S = 6
PM_CLOCK_CRYPTO_M = (1 << PM_CLOCK_CRYPTO_S)
PM_CLOCK_CRC32_S = 7
PM_CLOCK_CRC32_M = (1 << PM_CLOCK_CRC32_S)

# APB M
PM_CLOCK_PM_S = 0
PM_CLOCK_PM_M = (1 << PM_CLOCK_PM_S)

# --------------------------
# WU register offset
# --------------------------
WU_BASE_ADDRESS = 0x00060000

WU_CLOCKS_BU_OFFSET = 0x10

# --------------------------
# WU register fields
# --------------------------

# CLOCKS_BU



def pm_init():
    openocd.write_word(WU_BASE_ADDRESS + WU_CLOCKS_BU_OFFSET, 0x202)
    openocd.write_word(PM_BASE_ADDRESS + PM_Clk_APB_P_Set_OFFSET, 0xffffffff)
    openocd.write_word(PM_BASE_ADDRESS + PM_Clk_APB_M_Set_OFFSET, 0xffffffff)
    openocd.write_word(PM_BASE_ADDRESS + PM_Clk_AHB_Set_OFFSET, 0xffffffff)