#include "mik32_hal_pcc.h"
#include "mik32_hal_spifi.h"
#include "mik32_hal_spifi_w25.h"

#include "uart_lib.h"
#include "xprintf.h"

/**
 * @file main.c
 *
 * @brief Пример демонстрирует чтение и запись значений во внешнюю флеш память Winbond W25 по Standard (Single) SPI
 */

// extern char __HEAP_START[];
const int BUFFER4K_SIZE = 4 * 1024;
extern uint8_t *BUFFER4K[];
extern uint32_t *BUFFER_STATUS[];

register uint32_t address_reg asm("x31");

void SystemClock_Config(void);

void read_flash(SPIFI_HandleTypeDef *spifi, uint32_t address, uint8_t dataLength, uint8_t *dataBytes);

int main()
{
    // *BUFFER_STATUS = 1;
    SystemClock_Config();

    UART_Init(UART_0, 287, UART_CONTROL1_TE_M | UART_CONTROL1_M_8BIT_M, 0, 0);
    xprintf("START DRIVER\n");

    SPIFI_HandleTypeDef spifi = {
        .Instance = SPIFI_CONFIG,
    };

    HAL_SPIFI_MspInit(&spifi);
    xprintf("msp init complete\n");

    HAL_SPIFI_Reset(&spifi);
    xprintf("spifi reset complete\n");

    // xprintf("BUFFER4K = 0x%08x\n", BUFFER4K);

    *BUFFER_STATUS = 1;
    
    HAL_DelayMs(1);

    while (1)
    {
        uint32_t address = address_reg;
        xprintf("ERASE SECTOR 0x%08x\n", address);
        // xprintf("*BUFFER_STATUS 0x%08x\n", *BUFFER_STATUS);
        // asm ("wfi");

        // *BUFFER_STATUS = 1;

        // HAL_SPIFI_Reset(&spifi);
        // HAL_SPIFI_WaitResetClear(&spifi, HAL_SPIFI_TIMEOUT);

        HAL_SPIFI_W25_SectorErase4K(&spifi, address);

        int result = 0;

        for (int ad = 0; ad < BUFFER4K_SIZE; ad += 256)
        {
            // xprintf("Write Page 0x%08x from 0x%08x\n", ad + address, (uint8_t *)((uint32_t)BUFFER4K + ad));
            HAL_SPIFI_W25_PageProgram(&spifi, address + ad, 256, (uint8_t *)((uint32_t)BUFFER4K + ad));

            uint8_t rb[256] = { 0 };
            HAL_SPIFI_W25_ReadData(&spifi, address + ad, 256, rb);

            for (uint32_t b = 0; b < 256; b++)
            {
                if (*(uint8_t *)((uint32_t)BUFFER4K + ad + b) != rb[b])
                {
                    xprintf("addr[0x%08x:0x%02x] buf:mem = 0x%02x != 0x%02x\n", (uint32_t)BUFFER4K + ad + b, b, *(uint8_t *)((uint32_t)BUFFER4K + ad + b), rb[b]);
                    result = 2;
                    // break;
                }
            }
        }

        *BUFFER_STATUS = result;
        HAL_DelayMs(1);
        // asm ("wfi");
    }

    while (1)
        ;
}

void SystemClock_Config(void)
{
    PCC_InitTypeDef PCC_OscInit = {0};

    PCC_OscInit.OscillatorEnable = PCC_OSCILLATORTYPE_ALL;
    PCC_OscInit.FreqMon.OscillatorSystem = PCC_OSCILLATORTYPE_OSC32M;
    PCC_OscInit.FreqMon.ForceOscSys = PCC_FORCE_OSC_SYS_UNFIXED;
    PCC_OscInit.FreqMon.Force32KClk = PCC_FREQ_MONITOR_SOURCE_OSC32K;
    PCC_OscInit.AHBDivider = 0;
    PCC_OscInit.APBMDivider = 0;
    PCC_OscInit.APBPDivider = 0;
    PCC_OscInit.HSI32MCalibrationValue = 128;
    PCC_OscInit.LSI32KCalibrationValue = 128;
    PCC_OscInit.RTCClockSelection = PCC_RTC_CLOCK_SOURCE_AUTO;
    PCC_OscInit.RTCClockCPUSelection = PCC_CPU_RTC_CLOCK_SOURCE_OSC32K;
    HAL_PCC_Config(&PCC_OscInit);
}
