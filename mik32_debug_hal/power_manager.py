from tclrpc import OpenOcdTclRpc
import mik32_debug_hal.registers.memory_map as mem_map
import mik32_debug_hal.registers.bitfields.power_manager as pm_fields
import mik32_debug_hal.registers.bitfields.wakeup as wake_fields


def pm_init(openocd: OpenOcdTclRpc):

    WU_CLOCKS_default = 128 << wake_fields.CLOCKS_BU_ADJ_RC32K_S

    AHB_default = (
        pm_fields.CLOCK_AHB_CPU_M |
        pm_fields.CLOCK_AHB_EEPROM_M |
        pm_fields.CLOCK_AHB_RAM_M |
        pm_fields.CLOCK_AHB_SPIFI_M |
        pm_fields.CLOCK_AHB_TCB_M |
        pm_fields.CLOCK_AHB_DMA_M
    )
    # 0x1F
    APB_M_default = (
        pm_fields.CLOCK_APB_M_PM_M |
        pm_fields.CLOCK_APB_M_PAD_CONFIG_M |
        pm_fields.CLOCK_APB_M_WU_M
    )
    # 0x89
    APB_P_default = pm_fields.CLOCK_APB_P_GPIO_2_M
    # 0x00

    openocd.halt()
    openocd.write_word(mem_map.WU_CLOCKS_BU_OFFSET, WU_CLOCKS_default)
    openocd.write_word(mem_map.PM_Clk_APB_P_Set_OFFSET, APB_P_default)
    openocd.write_word(mem_map.PM_Clk_APB_M_Set_OFFSET, APB_M_default)
    openocd.write_word(mem_map.PM_Clk_AHB_Set_OFFSET, AHB_default)
