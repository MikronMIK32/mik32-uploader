#include "mik32_hal_pcc.h"
#include "mik32_hal_eeprom.h"

#include "uart_lib.h"
#include "xprintf.h"


const int BUFFER_SIZE = 8 * 1024;
extern uint8_t *BUFFER[];
extern uint32_t BUFFER_STATUS[];

#define EEPROM_OP_TIMEOUT 100000
#define USART_TIMEOUT 1000
#define EEPROM_PAGE_WORDS 32
#define EEPROM_PAGE_COUNT 64

register uint32_t max_address_reg asm("x31");

void SystemClock_Config(void);
void EEPROM_Init(void);

HAL_EEPROM_HandleTypeDef heeprom;

int main()
{
    SystemClock_Config();

#ifdef UART_DEBUG
    UART_Init(UART_0, 278, UART_CONTROL1_TE_M | UART_CONTROL1_M_8BIT_M, 0, 0);
    xprintf("START DRIVER\n");
#endif

    HAL_EEPROM_HandleTypeDef heeprom = {
        .Instance = EEPROM_REGS,
    };

    HAL_EEPROM_Erase(&heeprom, 0, EEPROM_PAGE_WORDS, HAL_EEPROM_WRITE_ALL, EEPROM_OP_TIMEOUT);

    int result = 0;
    for (int ad = 0; ad < max_address_reg; ad += (EEPROM_PAGE_WORDS * 4))
    {
#ifdef UART_DEBUG
        xprintf("Write Page 0x%04x from 0x%08x\n", ad, (uint8_t *)((uint32_t)BUFFER + ad));
#endif

        HAL_EEPROM_Write(
            &heeprom,
            ad,
            (uint32_t *)((uint32_t)BUFFER + ad),
            EEPROM_PAGE_WORDS,
            HAL_EEPROM_WRITE_SINGLE,
            EEPROM_OP_TIMEOUT);

        uint8_t rb[EEPROM_PAGE_WORDS * 4] = {0};

        HAL_EEPROM_Read(&heeprom, ad, (uint32_t *)rb, EEPROM_PAGE_WORDS, EEPROM_OP_TIMEOUT);

        for (uint32_t b = 0; b < (EEPROM_PAGE_WORDS * 4); b++)
        {
            uint8_t ebuf = *(uint8_t *)((uint32_t)BUFFER + ad + b);
            if (ebuf != rb[b])
            {
#ifdef UART_DEBUG
                xprintf("addr[0x%04x:0x%08x] buf:mem = 0x%02x != 0x%02x\n", (uint32_t)BUFFER + ad + b, 0x01000000 + ad + b, ebuf, rb[b]);
#endif
                result = 2;
                goto error_exit;
            }
        }
    }

    error_exit:

    *BUFFER_STATUS = result;
    // asm ("wfi");

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

void EEPROM_Init()
{
    heeprom.Instance = EEPROM_REGS;
    heeprom.Mode = HAL_EEPROM_MODE_TWO_STAGE;
    heeprom.ErrorCorrection = HAL_EEPROM_ECC_ENABLE;
    heeprom.EnableInterrupt = HAL_EEPROM_SERR_DISABLE;

    HAL_EEPROM_Init(&heeprom);
    HAL_EEPROM_CalculateTimings(&heeprom, OSC_SYSTEM_VALUE);
}
