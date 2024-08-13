from enum import Enum
from typing import Dict, List, Union
import time
from tclrpc import TclException
from tclrpc import OpenOcdTclRpc
from mik32_dma import DMA, ChannelMode, ChannelIndex, ChannelAck, ChannelIncrement, ChannelPriority, ChannelRequest, ChannelSize


# --------------------------
# SPIFI register offset
# --------------------------
SPIFI_REGS_BASE_ADDRESS = 0x00070000

SPIFI_CONFIG_CTRL = SPIFI_REGS_BASE_ADDRESS + 0x000
SPIFI_CONFIG_CMD = SPIFI_REGS_BASE_ADDRESS + 0x004
SPIFI_CONFIG_ADDR = SPIFI_REGS_BASE_ADDRESS + 0x008
SPIFI_CONFIG_IDATA = SPIFI_REGS_BASE_ADDRESS + 0x00C
SPIFI_CONFIG_CLIMIT = SPIFI_REGS_BASE_ADDRESS + 0x010
SPIFI_CONFIG_DATA32 = SPIFI_REGS_BASE_ADDRESS + 0x014
SPIFI_CONFIG_MCMD = SPIFI_REGS_BASE_ADDRESS + 0x018
SPIFI_CONFIG_STAT = SPIFI_REGS_BASE_ADDRESS + 0x01C

# --------------------------
# SPIFI register fields
# --------------------------
# CTRL
SPIFI_CONFIG_CTRL_TIMEOUT_S = 0
SPIFI_CONFIG_CTRL_TIMEOUT_M = (0xFFFF << SPIFI_CONFIG_CTRL_TIMEOUT_S)


def SPIFI_CONFIG_CTRL_TIMEOUT(v):
    return (((v) << SPIFI_CONFIG_CTRL_TIMEOUT_S) & SPIFI_CONFIG_CTRL_TIMEOUT_M)


SPIFI_CONFIG_CTRL_CSHIGH_S = 16
SPIFI_CONFIG_CTRL_CSHIGH_M = (0xF << SPIFI_CONFIG_CTRL_CSHIGH_S)


def SPIFI_CONFIG_CTRL_CSHIGH(v):
    return (((v) << SPIFI_CONFIG_CTRL_CSHIGH_S) & SPIFI_CONFIG_CTRL_CSHIGH_M)


SPIFI_CONFIG_CTRL_CACHE_EN_S = 20
SPIFI_CONFIG_CTRL_CACHE_EN_M = (0x1 << SPIFI_CONFIG_CTRL_CACHE_EN_S)
SPIFI_CONFIG_CTRL_D_CACHE_DIS_S = 21
SPIFI_CONFIG_CTRL_D_CACHE_DIS_M = (0x1 << SPIFI_CONFIG_CTRL_D_CACHE_DIS_S)
SPIFI_CONFIG_CTRL_INTEN_S = 22
SPIFI_CONFIG_CTRL_INTEN_M = (0x1 << SPIFI_CONFIG_CTRL_INTEN_S)
SPIFI_CONFIG_CTRL_MODE3_S = 23
SPIFI_CONFIG_CTRL_MODE3_M = (0x1 << SPIFI_CONFIG_CTRL_MODE3_S)
SPIFI_CONFIG_CTRL_SCK_DIV_S = 24
SPIFI_CONFIG_CTRL_SCK_DIV_M = (0x7 << SPIFI_CONFIG_CTRL_SCK_DIV_S)


def SPIFI_CONFIG_CTRL_SCK_DIV(v):
    return (((v) << SPIFI_CONFIG_CTRL_SCK_DIV_S) & SPIFI_CONFIG_CTRL_SCK_DIV_M)


SPIFI_CONFIG_CTRL_PREFETCH_DIS_S = 27
SPIFI_CONFIG_CTRL_PREFETCH_DIS_M = (0x1 << SPIFI_CONFIG_CTRL_PREFETCH_DIS_S)
SPIFI_CONFIG_CTRL_DUAL_S = 28
SPIFI_CONFIG_CTRL_DUAL_M = (0x1 << SPIFI_CONFIG_CTRL_DUAL_S)
SPIFI_CONFIG_CTRL_RFCLK_S = 29
SPIFI_CONFIG_CTRL_RFCLK_M = (0x1 << SPIFI_CONFIG_CTRL_RFCLK_S)
SPIFI_CONFIG_CTRL_FBCLK_S = 30
SPIFI_CONFIG_CTRL_FBCLK_M = (0x1 << SPIFI_CONFIG_CTRL_FBCLK_S)
SPIFI_CONFIG_CTRL_DMAEN_S = 31
SPIFI_CONFIG_CTRL_DMAEN_M = (0x1 << SPIFI_CONFIG_CTRL_DMAEN_S)

# CMD
SPIFI_CONFIG_CMD_DATALEN_S = 0
SPIFI_CONFIG_CMD_DATALEN_M = (0x3FFF << SPIFI_CONFIG_CMD_DATALEN_S)


def SPIFI_CONFIG_CMD_DATALEN(v):
    return (((v) << SPIFI_CONFIG_CMD_DATALEN_S) & SPIFI_CONFIG_CMD_DATALEN_M)


SPIFI_CONFIG_CMD_POLL_S = 14
SPIFI_CONFIG_CMD_POLL_M = (0x1 << SPIFI_CONFIG_CMD_POLL_S)
SPIFI_CONFIG_CMD_DOUT_S = 15
SPIFI_CONFIG_CMD_DOUT_M = (0x1 << SPIFI_CONFIG_CMD_DOUT_S)
SPIFI_CONFIG_CMD_INTLEN_S = 16
SPIFI_CONFIG_CMD_INTLEN_M = (0x7 << SPIFI_CONFIG_CMD_INTLEN_S)
SPIFI_CONFIG_CMD_FIELDFORM_S = 19
SPIFI_CONFIG_CMD_FIELDFORM_M = (0x3 << SPIFI_CONFIG_CMD_FIELDFORM_S)
SPIFI_CONFIG_CMD_FRAMEFORM_S = 21
SPIFI_CONFIG_CMD_FRAMEFORM_M = (0x7 << SPIFI_CONFIG_CMD_FRAMEFORM_S)
SPIFI_CONFIG_CMD_OPCODE_S = 24
SPIFI_CONFIG_CMD_OPCODE_M = (0xFF << SPIFI_CONFIG_CMD_OPCODE_S)

SPIFI_CONFIG_CMD_DATALEN_BUSY_INDEX_S = 0
SPIFI_CONFIG_CMD_DATALEN_BUSY_DONE_VALUE_S = 3

SPIFI_CONFIG_CMD_FRAMEFORM_RESERVED = 0
SPIFI_CONFIG_CMD_FRAMEFORM_OPCODE_NOADDR = 1
SPIFI_CONFIG_CMD_FRAMEFORM_OPCODE_1ADDR = 2
SPIFI_CONFIG_CMD_FRAMEFORM_OPCODE_2ADDR = 3
SPIFI_CONFIG_CMD_FRAMEFORM_OPCODE_3ADDR = 4
SPIFI_CONFIG_CMD_FRAMEFORM_OPCODE_4ADDR = 5
SPIFI_CONFIG_CMD_FRAMEFORM_NOOPCODE_3ADDR = 6
SPIFI_CONFIG_CMD_FRAMEFORM_NOOPCODE_4ADDR = 7

SPIFI_CONFIG_CMD_FIELDFORM_ALL_SERIAL = 0
SPIFI_CONFIG_CMD_FIELDFORM_DATA_PARALLEL = 1
SPIFI_CONFIG_CMD_FIELDFORM_OPCODE_SERIAL = 2
SPIFI_CONFIG_CMD_FIELDFORM_ALL_PARALLEL = 3

# MCMD
SPIFI_CONFIG_MCMD_POLL_S = 14
SPIFI_CONFIG_MCMD_POLL_M = (0x1 << SPIFI_CONFIG_MCMD_POLL_S)
SPIFI_CONFIG_MCMD_DOUT_S = 15
SPIFI_CONFIG_MCMD_DOUT_M = (0x1 << SPIFI_CONFIG_MCMD_DOUT_S)
SPIFI_CONFIG_MCMD_INTLEN_S = 16
SPIFI_CONFIG_MCMD_INTLEN_M = (0x7 << SPIFI_CONFIG_MCMD_INTLEN_S)
SPIFI_CONFIG_MCMD_FIELDFORM_S = 19
SPIFI_CONFIG_MCMD_FIELDFORM_M = (0x3 << SPIFI_CONFIG_MCMD_FIELDFORM_S)
SPIFI_CONFIG_MCMD_FRAMEFORM_S = 21
SPIFI_CONFIG_MCMD_FRAMEFORM_M = (0x7 << SPIFI_CONFIG_MCMD_FRAMEFORM_S)
SPIFI_CONFIG_MCMD_OPCODE_S = 24
SPIFI_CONFIG_MCMD_OPCODE_M = (0xFF << SPIFI_CONFIG_MCMD_OPCODE_S)

# STATUS
SPIFI_CONFIG_STAT_MCINIT_S = 0
SPIFI_CONFIG_STAT_MCINIT_M = (0x1 << SPIFI_CONFIG_STAT_MCINIT_S)
SPIFI_CONFIG_STAT_CMD_S = 1
SPIFI_CONFIG_STAT_CMD_M = (0x1 << SPIFI_CONFIG_STAT_CMD_S)
SPIFI_CONFIG_STAT_RESET_S = 4
SPIFI_CONFIG_STAT_RESET_M = (0x1 << SPIFI_CONFIG_STAT_RESET_S)
SPIFI_CONFIG_STAT_INTRQ_S = 5
SPIFI_CONFIG_STAT_INTRQ_M = (0x1 << SPIFI_CONFIG_STAT_INTRQ_S)
SPIFI_CONFIG_STAT_VERSION_S = 24
SPIFI_CONFIG_STAT_VERSION_M = (0xFF << SPIFI_CONFIG_STAT_VERSION_S)

# --------------------------
# Commands
# --------------------------
SREG1_BUSY = 1

READ_LEN = 256
TIMEOUT = 1000

ENABLE_RESET_COMMAND = 0x66
RESET_COMMAND = 0x99

CHIP_ERASE_COMMAND = 0xC7
SECTOR_ERASE_COMMAND = 0x20

WRITE_ENABLE_COMMAND = 0x06
WRITE_DISABLE_COMMAND = 0x04

#DISABLE_QPI_COMMAND = 0xFF

MEM_CONFIG_COMMAND = 0x61
MEM_CONFIG_VALUE = 0x7F

READ_DATA_COMMAND = 0x03

FAST_READ_QUAD_OUTPUT_COMMAND = 0x6B

READ_SREG1_COMMAND = 0x05
READ_SREG2_COMMAND = 0x35
WRITE_SREG_COMMAND = 0x01

SREG2_QUAD_ENABLE = 9
SREG2_QUAD_ENABLE_S = (SREG2_QUAD_ENABLE-8)
SREG2_QUAD_ENABLE_M = 1 << SREG2_QUAD_ENABLE_S

PAGE_PROGRAM_COMMAND = 0x02

QUAD_PAGE_PROGRAM_COMMAND = 0x32

JEDEC_ID_COMMAND = 0x9F


class SREG_Num(Enum):
    SREG1 = 0x00
    SREG2 = 0x30


def spifi_intrq_clear(openocd: OpenOcdTclRpc):
    openocd.write_word(SPIFI_CONFIG_STAT, openocd.read_word(SPIFI_CONFIG_STAT) |
                       SPIFI_CONFIG_STAT_INTRQ_M)


INIT_DELAY = 0.001


def spifi_init_periphery(openocd: OpenOcdTclRpc):
    openocd.write_word(SPIFI_CONFIG_STAT, openocd.read_word(SPIFI_CONFIG_STAT) |
                    #    SPIFI_CONFIG_STAT_INTRQ_M |
                       SPIFI_CONFIG_STAT_RESET_M)
    # openocd.write_word(SPIFI_CONFIG_CTRL, openocd.read_word(
    #     SPIFI_CONFIG_CTRL) | (7 << SPIFI_CONFIG_CTRL_SCK_DIV_S))
    openocd.write_word(SPIFI_CONFIG_ADDR, 0x00)
    openocd.write_word(SPIFI_CONFIG_IDATA, 0x00)
    openocd.write_word(SPIFI_CONFIG_CLIMIT, 0x00)

    time.sleep(INIT_DELAY)


def spifi_init(openocd: OpenOcdTclRpc):
    print("MCU clock init", flush=True)

    spifi_init_periphery(openocd)

    control = openocd.read_word(SPIFI_CONFIG_CTRL)
    control |= SPIFI_CONFIG_CTRL_DMAEN_M
    openocd.write_word(SPIFI_CONFIG_CTRL, control)

    time.sleep(INIT_DELAY)


def spifi_init_memory(openocd: OpenOcdTclRpc):
    openocd.write_word(SPIFI_CONFIG_STAT, openocd.read_word(SPIFI_CONFIG_STAT) |
                       SPIFI_CONFIG_STAT_INTRQ_M |
                       SPIFI_CONFIG_STAT_RESET_M)
    # openocd.write_word(SPIFI_CONFIG_CTRL, openocd.read_word(
    #     SPIFI_CONFIG_CTRL) | (7 << SPIFI_CONFIG_CTRL_SCK_DIV_S))
    openocd.write_word(SPIFI_CONFIG_ADDR, 0x00)
    openocd.write_word(SPIFI_CONFIG_IDATA, 0x00)
    openocd.write_word(SPIFI_CONFIG_CLIMIT, 0x00)   
    openocd.write_word(SPIFI_CONFIG_MCMD, (0 << SPIFI_CONFIG_MCMD_INTLEN_S) |
                             (SPIFI_CONFIG_CMD_FIELDFORM_ALL_SERIAL << SPIFI_CONFIG_MCMD_FIELDFORM_S) |
                             (SPIFI_CONFIG_CMD_FRAMEFORM_OPCODE_3ADDR << SPIFI_CONFIG_MCMD_FRAMEFORM_S) |
                             (READ_DATA_COMMAND << SPIFI_CONFIG_MCMD_OPCODE_S))
    
    time.sleep(INIT_DELAY)


def SPIFI_WaitIntrqTimeout(openocd: OpenOcdTclRpc, timeout: int) -> int:
    timeout_inner = timeout
    while timeout_inner:
        timeout_inner -= 1
        if (openocd.read_word(SPIFI_CONFIG_STAT) & SPIFI_CONFIG_STAT_INTRQ_M) != 0:
            return 1
    return 0


def spifi_wait_intrq_timeout(openocd: OpenOcdTclRpc, error_message: str):
    if SPIFI_WaitIntrqTimeout(openocd, TIMEOUT) == 0:
        raise Exception(error_message)
        return


class SPIFI_Frameform(Enum):
    RESERVED = 0
    OPCODE_NOADDR = 1
    OPCODE_1ADDR = 2
    OPCODE_2ADDR = 3
    OPCODE_3ADDR = 4
    OPCODE_4ADDR = 5
    NOOPCODE_3ADDR = 6
    NOOPCODE_4ADDR = 7


class SPIFI_Fieldform(Enum):
    ALL_SERIAL = 0
    DATA_PARALLEL = 1
    OPCODE_SERIAL = 2
    ALL_PARALLEL = 3


class SPIFI_Direction(Enum):
    READ = 0
    WRITE = 1


def spifi_send_command(
        openocd: OpenOcdTclRpc,
        cmd: int,
        frameform: SPIFI_Frameform,
        fieldform: SPIFI_Fieldform,
        byte_count=0,
        address=0,
        idata=0,
        cache_limit=0,
        idata_length=0,
        direction=SPIFI_Direction.READ,
        data: List[int] = [],
        dma: Union[DMA, None] = None
) -> List[int]:
    if (dma is not None) and (direction == SPIFI_Direction.WRITE):
        openocd.write_memory(0x02003F00, 8, data)

        dma.channels[0].start(
            0x02003F00,
            SPIFI_CONFIG_DATA32,
            255
        )
    elif (dma is not None) and (direction == SPIFI_Direction.READ):
        dma.channels[1].start(
            SPIFI_CONFIG_DATA32,
            0x02003F00,
            255
        )

    openocd.write_memory(SPIFI_CONFIG_ADDR, 32, [address, idata])
    
    # # spifi_intrq_clear(openocd)
    # openocd.write_word(SPIFI_CONFIG_CMD, (cmd << SPIFI_CONFIG_CMD_OPCODE_S) |
    #                    (frameform.value << SPIFI_CONFIG_CMD_FRAMEFORM_S) |
    #                    (fieldform.value << SPIFI_CONFIG_CMD_FIELDFORM_S) |
    #                    (byte_count << SPIFI_CONFIG_CMD_DATALEN_S) |
    #                    (idata_length << SPIFI_CONFIG_CMD_INTLEN_S) |
    #                    (direction.value << SPIFI_CONFIG_CMD_DOUT_S))
    # # spifi_wait_intrq_timeout(openocd, "Timeout executing write enable command")

    cmd_write_value = ((cmd << SPIFI_CONFIG_CMD_OPCODE_S) |
                       (frameform.value << SPIFI_CONFIG_CMD_FRAMEFORM_S) |
                       (fieldform.value << SPIFI_CONFIG_CMD_FIELDFORM_S) |
                       (byte_count << SPIFI_CONFIG_CMD_DATALEN_S) |
                       (idata_length << SPIFI_CONFIG_CMD_INTLEN_S) |
                       (direction.value << SPIFI_CONFIG_CMD_DOUT_S))

    openocd.write_memory(SPIFI_CONFIG_CMD, 32, [cmd_write_value])

    if direction == SPIFI_Direction.READ:
        out_list = []
        if dma is not None:
            dma.dma_wait(dma.channels[1], 0.1)
            out_list.extend(openocd.read_memory(0x02003F00, 8, byte_count))

            return out_list
        else:
            for i in range(byte_count):
                out_list.append(openocd.read_memory(SPIFI_CONFIG_DATA32, 8, 1)[0])
            return out_list

    if direction == SPIFI_Direction.WRITE:
        if dma is not None:
            dma.dma_wait(dma.channels[0], 0.1)
        else:
            if (byte_count % 4) == 0:
                for i in range(0, byte_count, 4):
                    openocd.write_memory(SPIFI_CONFIG_DATA32, 32, [
                                        data[i] + data[i+1] * 256 + data[i+2] * 256 * 256 + data[i+3] * 256 * 256 * 256])
            else:
                for i in range(byte_count):
                    openocd.write_memory(SPIFI_CONFIG_DATA32, 8, [data[i]])

    return []


def spifi_write_enable(openocd: OpenOcdTclRpc):
    spifi_send_command(openocd, WRITE_ENABLE_COMMAND,
                       SPIFI_Frameform.OPCODE_NOADDR, SPIFI_Fieldform.ALL_SERIAL)


def spifi_read_sreg(openocd: OpenOcdTclRpc, sreg: SREG_Num) -> int:
    return spifi_send_command(
        openocd, 
        READ_SREG1_COMMAND | sreg.value, 
        SPIFI_Frameform.OPCODE_NOADDR, 
        SPIFI_Fieldform.ALL_SERIAL, 
        byte_count=1
    )[0]


def spifi_write_sreg(openocd: OpenOcdTclRpc, sreg1: int, sreg2: int):
#    spifi_send_command(openocd, DISABLE_QPI_COMMAND,
#                       SPIFI_Frameform.OPCODE_NOADDR, SPIFI_Fieldform.ALL_PARALLEL)
    spifi_write_enable(openocd)
    spifi_send_command(
        openocd, 
        WRITE_SREG_COMMAND, 
        SPIFI_Frameform.OPCODE_NOADDR, 
        SPIFI_Fieldform.ALL_SERIAL, 
        byte_count=2, 
        direction=SPIFI_Direction.WRITE, 
        data=[sreg1, sreg2]
    )
    spifi_wait_busy(openocd)


def spifi_wait_busy(openocd: OpenOcdTclRpc):
    while 1:
        sreg1 = spifi_read_sreg(openocd, SREG_Num.SREG1)
        if not (sreg1 & SREG1_BUSY):
            break

RESET_DELAY = 0.001

def spifi_chip_reset(openocd: OpenOcdTclRpc):
    #print("Sending 'Reset' to external chip in SPI mode", flush=True)
    spifi_send_command(openocd, ENABLE_RESET_COMMAND,
                       SPIFI_Frameform.OPCODE_NOADDR, SPIFI_Fieldform.ALL_SERIAL)
    spifi_send_command(openocd, RESET_COMMAND,
                       SPIFI_Frameform.OPCODE_NOADDR, SPIFI_Fieldform.ALL_SERIAL)
    time.sleep(RESET_DELAY)


def spifi_chip_reset_qpi(openocd: OpenOcdTclRpc):
    #print("Sending 'Reset' to external chip in QPI mode", flush=True)
    spifi_send_command(openocd, ENABLE_RESET_COMMAND,
                       SPIFI_Frameform.OPCODE_NOADDR, SPIFI_Fieldform.ALL_PARALLEL)
    spifi_send_command(openocd, RESET_COMMAND,
                       SPIFI_Frameform.OPCODE_NOADDR, SPIFI_Fieldform.ALL_PARALLEL)
    time.sleep(RESET_DELAY)

#def spifi_chip_disable_qpi(openocd: OpenOcdTclRpc):
    #print("Sending 'Disable QPI' command to external flash chip in QPI mode.", flush=True)
#    spifi_send_command(openocd, DISABLE_QPI_COMMAND,
#                       SPIFI_Frameform.OPCODE_NOADDR, SPIFI_Fieldform.ALL_PARALLEL)


def spifi_chip_erase(openocd: OpenOcdTclRpc):
    print("Chip erase...", flush=True)
    spifi_send_command(openocd, CHIP_ERASE_COMMAND,
                       SPIFI_Frameform.OPCODE_NOADDR, SPIFI_Fieldform.ALL_SERIAL)


def spifi_sector_erase(openocd: OpenOcdTclRpc, address: int):
    print(f"Erase sector {address:#010x}...", flush=True)
    spifi_send_command(openocd, SECTOR_ERASE_COMMAND,
                       SPIFI_Frameform.OPCODE_3ADDR, SPIFI_Fieldform.ALL_SERIAL, address=address)


def spifi_read_data(openocd: OpenOcdTclRpc, address: int, byte_count: int, bin_data: List[int], dma: Union[DMA, None] = None, use_quad_spi=False) -> int:
    read_data: List[int] = []

    if (use_quad_spi):
        read_data = spifi_send_command(openocd, FAST_READ_QUAD_OUTPUT_COMMAND, SPIFI_Frameform.OPCODE_3ADDR, SPIFI_Fieldform.DATA_PARALLEL, byte_count=byte_count, address=address, idata_length=1, dma=dma)
    else:
        read_data = spifi_send_command(openocd, READ_DATA_COMMAND, SPIFI_Frameform.OPCODE_3ADDR, SPIFI_Fieldform.ALL_SERIAL, byte_count=byte_count, address=address, dma=dma)

    for i in range(byte_count):
        if read_data[i] != bin_data[i]:
            print(
                f"DATA[{i+address}] = {read_data[i]:#0x} expect {bin_data[i]:#0x}", flush=True)
            
            # spifi_init_periphery(openocd)
            # read_periph = spifi_send_command(openocd, READ_DATA_COMMAND, SPIFI_Frameform.OPCODE_3ADDR,
            #                        SPIFI_Fieldform.ALL_SERIAL, byte_count=1, address=(i+address))
            # print(
            #     f"DATA[{i+address}] = {read_periph[0]:#0x} expect {bin_data[i]:#0x}", flush=True)

            return 1

    return 0


def spifi_page_program(
        openocd: OpenOcdTclRpc,
        ByteAddress: int,
        data: List[int],
        byte_count: int,
        progress: str = "",
        dma: Union[DMA, None] = None
):
    print(f"Writing Flash page {ByteAddress:#010x}... {progress}", flush=True)
    if byte_count > 256:
        raise Exception("Byte count more than 256")

    spifi_write_enable(openocd)
    spifi_send_command(openocd, PAGE_PROGRAM_COMMAND, SPIFI_Frameform.OPCODE_3ADDR,
                       SPIFI_Fieldform.ALL_SERIAL, byte_count=byte_count, address=ByteAddress,
                       idata=0, cache_limit=0, direction=SPIFI_Direction.WRITE, data=data, dma=dma)
    spifi_wait_busy(openocd)


class EraseType(Enum):
    CHIP_ERASE = CHIP_ERASE_COMMAND
    SECTOR_ERASE = SECTOR_ERASE_COMMAND


def spifi_erase(openocd, erase_type: EraseType = EraseType.CHIP_ERASE, sectors: List[int] = []):
    if erase_type == EraseType.CHIP_ERASE:
        spifi_write_enable(openocd)
        spifi_chip_erase(openocd)
        spifi_wait_busy(openocd)
    elif erase_type == EraseType.SECTOR_ERASE:
        for sector in sectors:
            spifi_write_enable(openocd)
            spifi_sector_erase(openocd, sector)
            spifi_wait_busy(openocd)


def spifi_write(openocd: OpenOcdTclRpc, address: int, data: List[int], data_len: int):
    if data_len > 256:
        raise Exception("Byte count more than 256")

    spifi_page_program(openocd, address, data, data_len)

    print("written")


def spifi_write_file(bytes: List[int], openocd: OpenOcdTclRpc):
    # print(bytes)
    print(f"Write {len(bytes)} bytes")

    openocd.halt()
    spifi_init(openocd)
    spifi_erase(openocd)
    print("bin_data_len = ", len(bytes))
    address = 0

    for address in range(0, len(bytes), 256):
        if ((address + 256) > len(bytes)):
            break
        print("address = ", address)
        spifi_write(openocd, address, bytes, 256)
        if spifi_read_data(openocd, address, 256, bytes) == 1:
            return 1

    if (len(bytes) % 256) != 0:
        print(
            f"address = {address}, +{len(bytes) - address-1}[{address + len(bytes) - address-1}]")
        spifi_write(openocd, address, bytes, len(bytes) - address)
        if spifi_read_data(openocd, address, len(bytes) - address, bytes) == 1:
            return 1
    print("end")

    return 0


def spifi_quad_page_program(
    openocd: OpenOcdTclRpc,
    ByteAddress: int,
    data: List[int],
    byte_count: int,
    progress: str = "",
    dma: Union[DMA, None] = None
):
    print(f"Writing page {ByteAddress:#010x}... {progress}", flush=True)
    if byte_count > 256:
        raise Exception("Byte count more than 256")

    spifi_write_enable(openocd)
    spifi_send_command(openocd, QUAD_PAGE_PROGRAM_COMMAND, SPIFI_Frameform.OPCODE_3ADDR,
                       SPIFI_Fieldform.DATA_PARALLEL, byte_count=byte_count, address=ByteAddress,
                       idata=0, cache_limit=0, direction=SPIFI_Direction.WRITE, data=data, dma=dma)
    spifi_wait_busy(openocd)


def spifi_quad_enable(openocd):
    if (spifi_check_quad_enable(openocd) != True):
        spifi_write_sreg(
            openocd, 
            spifi_read_sreg(openocd, SREG_Num.SREG1), 
            spifi_read_sreg(openocd, SREG_Num.SREG2) | SREG2_QUAD_ENABLE_M
        )


#def spifi_quad_disable(openocd):
#    if (spifi_check_quad_enable(openocd) == True):
#        spifi_write_sreg(
#            openocd, 
#            spifi_read_sreg(openocd, SREG_Num.SREG1), 
#            spifi_read_sreg(openocd, SREG_Num.SREG2) & (0xFF ^ SREG2_QUAD_ENABLE_M)
#        )


def spifi_check_quad_enable(openocd):
    return (spifi_read_sreg(openocd, SREG_Num.SREG2) & SREG2_QUAD_ENABLE_M) != 0


def get_segments_list(pages_offsets: List[int], segment_size: int) -> List[int]:
    segments = set()
    for offset in pages_offsets:
        segments.add(offset & ~(segment_size - 1))
    return list(segments)


def check_pages(pages: Dict[int, List[int]], openocd: OpenOcdTclRpc, use_quad_spi=False, use_chip_erase=False):
    result = 0

    openocd.halt()
    spifi_init(openocd)
    
    # Сбрасываем микросхему в режиме QPI из всех состояний в нормальный SPI режим.
    spifi_chip_reset_qpi(openocd)
    
    # Сбрасываем микросхему в режиме SPI из всех состояний в нормальный SPI режим.
    spifi_chip_reset(openocd)

    JEDEC_ID = spifi_send_command(openocd, JEDEC_ID_COMMAND, SPIFI_Frameform.OPCODE_NOADDR, SPIFI_Fieldform.ALL_SERIAL, 3)

    print(f"JEDEC ID = {JEDEC_ID[0]:02x} {JEDEC_ID[1]:02x} {JEDEC_ID[2]:02x}")

    dma = DMA(openocd)
    dma.init()

    dma.channels[0].write_buffer = 0

    dma.channels[0].channel = ChannelIndex.CHANNEL_0
    dma.channels[0].priority = ChannelPriority.VERY_HIGH

    dma.channels[0].read_mode = ChannelMode.MEMORY
    dma.channels[0].read_increment = ChannelIncrement.ENABLE
    dma.channels[0].read_size = ChannelSize.WORD
    dma.channels[0].read_burst_size = 2
    dma.channels[0].read_request = ChannelRequest.SPIFI_REQUEST
    dma.channels[0].read_ack = ChannelAck.DISABLE

    dma.channels[0].write_mode = ChannelMode.PERIPHERY
    dma.channels[0].write_increment = ChannelIncrement.DISABLE
    dma.channels[0].write_size = ChannelSize.WORD
    dma.channels[0].write_burst_size = 2
    dma.channels[0].write_request = ChannelRequest.SPIFI_REQUEST
    dma.channels[0].write_ack = ChannelAck.DISABLE

    dma.channels[1].write_buffer = 0

    dma.channels[1].channel = ChannelIndex.CHANNEL_1
    dma.channels[1].priority = ChannelPriority.VERY_HIGH

    dma.channels[1].write_mode = ChannelMode.MEMORY
    dma.channels[1].write_increment = ChannelIncrement.ENABLE
    dma.channels[1].write_size = ChannelSize.WORD
    dma.channels[1].write_burst_size = 2
    dma.channels[1].write_request = ChannelRequest.SPIFI_REQUEST
    dma.channels[1].write_ack = ChannelAck.DISABLE

    dma.channels[1].read_mode = ChannelMode.PERIPHERY
    dma.channels[1].read_increment = ChannelIncrement.DISABLE
    dma.channels[1].read_size = ChannelSize.WORD
    dma.channels[1].read_burst_size = 2
    dma.channels[1].read_request = ChannelRequest.SPIFI_REQUEST
    dma.channels[1].read_ack = ChannelAck.DISABLE

    if (use_quad_spi):
        print("Using Quad SPI")
        spifi_quad_enable(openocd)
    else:
        print("Using Single SPI")
    #    spifi_quad_disable(openocd)

    pages_offsets = list(pages)

    for index, page_offset in enumerate(pages_offsets):
        print(f"Check page {page_offset:#010x}... {(index*100)//pages_offsets.__len__()}%", flush=True)
        page_bytes = pages[page_offset]

        result = spifi_read_data(openocd, page_offset, 256, page_bytes, dma=dma, use_quad_spi=use_quad_spi)

        if result == 1:
            print("Data error")
            #if (use_quad_spi):
            #    spifi_quad_disable(openocd)
            return result

    if result == 0:
        print("SPIFI pages checking completed", flush=True)
    return 0

# # PROFILING IMPORTS
# import cProfile, pstats, io
# from pstats import SortKey

def write_pages(pages: Dict[int, List[int]], openocd: OpenOcdTclRpc, use_quad_spi=False, use_chip_erase=False):
    result = 0

    # # PROFILING INIT
    # pr = cProfile.Profile()
    # pr.enable()
    # # PROFILING INIT END

    openocd.halt()
    spifi_init(openocd)
    
    # Сбрасываем микросхему в режиме QPI из всех состояний в нормальный SPI режим.
    spifi_chip_reset_qpi(openocd)
    
    # Сбрасываем микросхему в режиме SPI из всех состояний в нормальный SPI режим.
    spifi_chip_reset(openocd)

    JEDEC_ID = spifi_send_command(openocd, JEDEC_ID_COMMAND, SPIFI_Frameform.OPCODE_NOADDR, SPIFI_Fieldform.ALL_SERIAL, 3)

    print(f"JEDEC ID = {JEDEC_ID[0]:02x} {JEDEC_ID[1]:02x} {JEDEC_ID[2]:02x}")

    dma = DMA(openocd)
    dma.init()

    dma.channels[0].write_buffer = 0

    dma.channels[0].channel = ChannelIndex.CHANNEL_0
    dma.channels[0].priority = ChannelPriority.VERY_HIGH

    dma.channels[0].read_mode = ChannelMode.MEMORY
    dma.channels[0].read_increment = ChannelIncrement.ENABLE
    dma.channels[0].read_size = ChannelSize.WORD
    dma.channels[0].read_burst_size = 2
    dma.channels[0].read_request = ChannelRequest.SPIFI_REQUEST
    dma.channels[0].read_ack = ChannelAck.DISABLE

    dma.channels[0].write_mode = ChannelMode.PERIPHERY
    dma.channels[0].write_increment = ChannelIncrement.DISABLE
    dma.channels[0].write_size = ChannelSize.WORD
    dma.channels[0].write_burst_size = 2
    dma.channels[0].write_request = ChannelRequest.SPIFI_REQUEST
    dma.channels[0].write_ack = ChannelAck.DISABLE

    dma.channels[1].write_buffer = 0

    dma.channels[1].channel = ChannelIndex.CHANNEL_1
    dma.channels[1].priority = ChannelPriority.VERY_HIGH

    dma.channels[1].write_mode = ChannelMode.MEMORY
    dma.channels[1].write_increment = ChannelIncrement.ENABLE
    dma.channels[1].write_size = ChannelSize.WORD
    dma.channels[1].write_burst_size = 2
    dma.channels[1].write_request = ChannelRequest.SPIFI_REQUEST
    dma.channels[1].write_ack = ChannelAck.DISABLE

    dma.channels[1].read_mode = ChannelMode.PERIPHERY
    dma.channels[1].read_increment = ChannelIncrement.DISABLE
    dma.channels[1].read_size = ChannelSize.WORD
    dma.channels[1].read_burst_size = 2
    dma.channels[1].read_request = ChannelRequest.SPIFI_REQUEST
    dma.channels[1].read_ack = ChannelAck.DISABLE

    if use_chip_erase:
        spifi_erase(openocd, EraseType.CHIP_ERASE)
    else:
        spifi_erase(openocd, EraseType.SECTOR_ERASE,
                    get_segments_list(list(pages), 4*1024))

        # for addr in range(0, 4096*2, 256):
        #     result = spifi_read_data(openocd, addr, 256, [0xFF]*256, dma=dma)

        #     if result == 1:
        #         print("Data error")
        #         return result

    print("Quad Enable", spifi_check_quad_enable(openocd))

    if (use_quad_spi):
        print("Using Quad SPI")
        spifi_quad_enable(openocd)
    else:
        print("Using Single SPI")
        #spifi_quad_disable(openocd)
    
    # print("SREG1", spifi_read_sreg(openocd, SREG_Num.SREG1))
    # print("SREG2", spifi_read_sreg(openocd, SREG_Num.SREG2))

    pages_offsets = list(pages)

    for index, page_offset in enumerate(pages_offsets):
        page_bytes = pages[page_offset]

        if (use_quad_spi):
            spifi_quad_page_program(
                openocd, page_offset, page_bytes, 256, f"{(index*100)//pages_offsets.__len__()}%", dma=dma)
        else:
            spifi_page_program(openocd, page_offset, page_bytes,
                               256, f"{(index*100)//pages_offsets.__len__()}%", dma=dma)

        result = spifi_read_data(openocd, page_offset, 256, page_bytes, dma=dma, use_quad_spi=use_quad_spi)

        if result == 1:
            print("Data error")
            return result

    #if (use_quad_spi):
    #    spifi_quad_disable(openocd)

    # # PROFILING GET STATS
    # pr.disable()
    # s = io.StringIO()
    # sortby = SortKey.CUMULATIVE
    # ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
    # ps.print_stats()
    # print(s.getvalue())
    # # PROFILING GET STATS END

    if result == 0:
        # Прошивка страниц флеш памяти по SPIFI была завершена
        print("Flashing of flash memory pages via SPIFI has been completed", flush=True)
    return 0
