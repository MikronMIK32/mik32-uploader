from tclrpc import OpenOcdTclRpc
import mik32_debug_hal.registers.memory_map as mem_map
import mik32_debug_hal.registers.bitfields.power_manager as pm_fields
import mik32_debug_hal.registers.bitfields.wakeup as wake_fields

def pm_init(openocd: OpenOcdTclRpc) -> int:

    iter_count = 0
    max_iter_count = 2

    while True:
        print('Clock init... ', end='')

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
        # APB_P_default = pm_fields.CLOCK_APB_P_GPIO_2_M
        APB_P_default = 0
        # 0x00

        # openocd.halt()
        # openocd.write_word(mem_map.WU_CLOCKS_BU_OFFSET, WU_CLOCKS_default)
        # openocd.write_word(mem_map.PM_Clk_APB_P_Set_OFFSET, APB_P_default)
        # openocd.write_word(mem_map.PM_Clk_APB_M_Set_OFFSET, APB_M_default)
        # openocd.write_word(mem_map.PM_Clk_AHB_Set_OFFSET, AHB_default)

        openocd.halt()
        openocd.write_word(mem_map.PM_Clk_APB_P_Clear_OFFSET, ~APB_P_default)
        openocd.write_word(mem_map.PM_Clk_APB_P_Set_OFFSET, APB_P_default)
        # openocd.halt()
        openocd.write_word(mem_map.PM_Clk_AHB_Clear_OFFSET, ~AHB_default)
        openocd.write_word(mem_map.PM_Clk_AHB_Set_OFFSET, AHB_default)
        # openocd.halt()
        openocd.write_word(mem_map.PM_Clk_APB_M_Clear_OFFSET, ~APB_M_default)
        openocd.write_word(mem_map.PM_Clk_APB_M_Set_OFFSET, APB_M_default)
        # openocd.halt()
        openocd.write_word(mem_map.WU_CLOCKS_BU_OFFSET, WU_CLOCKS_default)
        # openocd.halt()


        AHB_real = openocd.read_word(mem_map.PM_Clk_AHB_Set_OFFSET)
        APB_M_real = openocd.read_word(mem_map.PM_Clk_APB_M_Set_OFFSET)
        APB_P_real = openocd.read_word(mem_map.PM_Clk_APB_P_Set_OFFSET)
        WU_CLOCKS_real = openocd.read_word(mem_map.WU_CLOCKS_BU_OFFSET)

        if (
            (WU_CLOCKS_real == WU_CLOCKS_default) and
            (AHB_real == AHB_default) and
            (APB_M_real == APB_M_default) and
            (APB_P_real == APB_P_default)
        ):
            print('OK!')
            return 0
        else:
            print('\nPM initialization results:')
            print(f'wu    план 0x{WU_CLOCKS_default:08x} факт 0x{WU_CLOCKS_real:08x}')
            print(f'ahb   план 0x{AHB_default:08x} факт 0x{AHB_real:08x}')
            print(f'apb_m план 0x{APB_M_default:08x} факт 0x{APB_M_real:08x}')
            print(f'apb_p план 0x{APB_P_default:08x} факт 0x{APB_P_real:08x}')
            iter_count += 1
            if iter_count < max_iter_count:
                print(f'ERROR: PM initialization failed, retry #{iter_count}...', flush=True)
            else:
                print('ERROR: PM initialization failed, aborting', flush=True)
                return 1
