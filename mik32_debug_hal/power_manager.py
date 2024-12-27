from tclrpc import OpenOcdTclRpc
import mik32_debug_hal.registers.memory_map as mem_map
import mik32_debug_hal.registers.bitfields.power_manager as pm_fields
import mik32_debug_hal.registers.bitfields.wakeup as wake_fields


def pm_init(openocd: OpenOcdTclRpc) -> int:
    """ Настройка тактирования

    Ключевые аргументы:
    openocd - объект для доступа к интерфейсу Tcl OpenOCD

    Возвращаемое значение:
    0 - успех
    1 - ошибка
    """

    iter = 1
    max_iter = 2  # число попыток записи регистров

    while True:
        print('Clock init... ', end='')

        # определение начальных значений регистров
        APB_P_default = 0

        AHB_default = (
            pm_fields.CLOCK_AHB_CPU_M |
            pm_fields.CLOCK_AHB_EEPROM_M |
            pm_fields.CLOCK_AHB_RAM_M |
            pm_fields.CLOCK_AHB_SPIFI_M |
            pm_fields.CLOCK_AHB_TCB_M |
            pm_fields.CLOCK_AHB_DMA_M
        )

        APB_M_default = (
            pm_fields.CLOCK_APB_M_PM_M |
            pm_fields.CLOCK_APB_M_PAD_CONFIG_M |
            pm_fields.CLOCK_APB_M_WU_M
        )

        WU_CLOCKS_default = 128 << wake_fields.CLOCKS_BU_ADJ_RC32K_S

        # запись начальных значений в регистры
        openocd.halt()

        openocd.write_word(mem_map.PM_Clk_APB_P_Clear_OFFSET, ~APB_P_default)
        openocd.write_word(mem_map.PM_Clk_APB_P_Set_OFFSET, APB_P_default)

        openocd.write_word(mem_map.PM_Clk_AHB_Clear_OFFSET, ~AHB_default)
        openocd.write_word(mem_map.PM_Clk_AHB_Set_OFFSET, AHB_default)

        openocd.write_word(mem_map.PM_Clk_APB_M_Clear_OFFSET, ~APB_M_default)
        openocd.write_word(mem_map.PM_Clk_APB_M_Set_OFFSET, APB_M_default)

        openocd.write_word(mem_map.WU_CLOCKS_BU_OFFSET, WU_CLOCKS_default)

        # проверка записи на случай неожиданного ресета и перезаписи прошивкой
        APB_P_real = openocd.read_word(mem_map.PM_Clk_APB_P_Set_OFFSET)
        AHB_real = openocd.read_word(mem_map.PM_Clk_AHB_Set_OFFSET)
        APB_M_real = openocd.read_word(mem_map.PM_Clk_APB_M_Set_OFFSET)
        WU_CLOCKS_real = openocd.read_word(mem_map.WU_CLOCKS_BU_OFFSET)

        if (
            (WU_CLOCKS_real == WU_CLOCKS_default) and
            (AHB_real == AHB_default) and
            (APB_M_real == APB_M_default) and
            (APB_P_real == APB_P_default)
        ):
            print('OK!')
            return 0

        print('\nPM initialization results:')
        print(
            f'wu    def 0x{WU_CLOCKS_default:08x} real 0x{WU_CLOCKS_real:08x}')
        print(f'ahb   def 0x{AHB_default:08x} real 0x{AHB_real:08x}')
        print(f'apb_m def 0x{APB_M_default:08x} real 0x{APB_M_real:08x}')
        print(f'apb_p def 0x{APB_P_default:08x} real 0x{APB_P_real:08x}')

        iter += 1
        if iter > max_iter:
            print('ERROR: PM initialization failed, aborting', flush=True)
            return 1

        print(f'ERROR: PM initialization failed, retry #{iter}...', flush=True)
