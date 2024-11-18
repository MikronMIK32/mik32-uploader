from enum import Enum
import time
from typing import List, Union
from tclrpc import OpenOcdTclRpc
import mik32_debug_hal.spifi as spifi
import mik32_debug_hal.dma as dma


# --------------------------
# Commands
# --------------------------
SREG1_BUSY = 1

READ_LEN = 256

ENABLE_RESET_COMMAND = 0x66
RESET_COMMAND = 0x99

CHIP_ERASE_COMMAND = 0xC7
SECTOR_ERASE_COMMAND = 0x20

WRITE_ENABLE_COMMAND = 0x06
WRITE_DISABLE_COMMAND = 0x04

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


class FlashError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return ("ERROR: " + repr(self.value))


class SREG_Num(Enum):
    SREG1 = 0x00
    SREG2 = 0x30


def write_enable(openocd: OpenOcdTclRpc):
    spifi.send_command(openocd, WRITE_ENABLE_COMMAND,
                             spifi.Frameform.OPCODE_NOADDR, spifi.Fieldform.ALL_SERIAL)


def read_sreg(openocd: OpenOcdTclRpc, sreg: SREG_Num) -> int:
    return spifi.send_command(
        openocd,
        READ_SREG1_COMMAND | sreg.value,
        spifi.Frameform.OPCODE_NOADDR,
        spifi.Fieldform.ALL_SERIAL,
        byte_count=1
    )[0]


def write_sreg(openocd: OpenOcdTclRpc, sreg1: int, sreg2: int):
    write_enable(openocd)
    spifi.send_command(
        openocd,
        WRITE_SREG_COMMAND,
        spifi.Frameform.OPCODE_NOADDR,
        spifi.Fieldform.ALL_SERIAL,
        byte_count=2,
        direction=spifi.Direction.WRITE,
        data=[sreg1, sreg2]
    )
    wait_busy(openocd)


def wait_busy(openocd: OpenOcdTclRpc):
    while 1:
        sreg1 = read_sreg(openocd, SREG_Num.SREG1)
        if not (sreg1 & SREG1_BUSY):
            break


RESET_DELAY = 0.001


def chip_reset(openocd: OpenOcdTclRpc):
    spifi.send_command(openocd, ENABLE_RESET_COMMAND,
                             spifi.Frameform.OPCODE_NOADDR, spifi.Fieldform.ALL_SERIAL)
    spifi.send_command(openocd, RESET_COMMAND,
                             spifi.Frameform.OPCODE_NOADDR, spifi.Fieldform.ALL_SERIAL)
    time.sleep(RESET_DELAY)


def chip_reset_qpi(openocd: OpenOcdTclRpc):
    spifi.send_command(openocd, ENABLE_RESET_COMMAND,
                             spifi.Frameform.OPCODE_NOADDR, spifi.Fieldform.ALL_PARALLEL)
    spifi.send_command(openocd, RESET_COMMAND,
                             spifi.Frameform.OPCODE_NOADDR, spifi.Fieldform.ALL_PARALLEL)
    time.sleep(RESET_DELAY)


def chip_erase(openocd: OpenOcdTclRpc):
    print("Chip erase...", flush=True)
    spifi.send_command(openocd, CHIP_ERASE_COMMAND,
                             spifi.Frameform.OPCODE_NOADDR, spifi.Fieldform.ALL_SERIAL)


def sector_erase(openocd: OpenOcdTclRpc, address: int):
    print(f"Erase sector {address:#010x}...", flush=True)
    spifi.send_command(openocd, SECTOR_ERASE_COMMAND,
                             spifi.Frameform.OPCODE_3ADDR, spifi.Fieldform.ALL_SERIAL, address=address)


def read_data(openocd: OpenOcdTclRpc, address: int, byte_count: int, bin_data: List[int], dma: Union[dma.DMA, None] = None, use_quad_spi=False) -> int:
    read_data: List[int] = []

    if (use_quad_spi):
        read_data = spifi.send_command(openocd, FAST_READ_QUAD_OUTPUT_COMMAND, spifi.Frameform.OPCODE_3ADDR,
                                             spifi.Fieldform.DATA_PARALLEL, byte_count=byte_count, address=address, idata_length=1, dma=dma)
    else:
        read_data = spifi.send_command(openocd, READ_DATA_COMMAND, spifi.Frameform.OPCODE_3ADDR,
                                             spifi.Fieldform.ALL_SERIAL, byte_count=byte_count, address=address, dma=dma)

    for i in range(byte_count):
        if read_data[i] != bin_data[i]:
            print(
                f"DATA[{i+address}] = {read_data[i]:#0x} expect {bin_data[i]:#0x}", flush=True)

            return 1

    return 0


def page_program(
        openocd: OpenOcdTclRpc,
        ByteAddress: int,
        data: List[int],
        byte_count: int,
        progress: str = "",
        dma: Union[dma.DMA, None] = None
):
    print(f"Writing Flash page {ByteAddress:#010x}... {progress}", flush=True)
    if byte_count > 256:
        raise FlashError("Byte count more than 256")

    write_enable(openocd)
    spifi.send_command(openocd, PAGE_PROGRAM_COMMAND, spifi.Frameform.OPCODE_3ADDR,
                             spifi.Fieldform.ALL_SERIAL, byte_count=byte_count, address=ByteAddress,
                             idata=0, cache_limit=0, direction=spifi.Direction.WRITE, data=data, dma=dma)
    wait_busy(openocd)


class EraseType(Enum):
    CHIP_ERASE = CHIP_ERASE_COMMAND
    SECTOR_ERASE = SECTOR_ERASE_COMMAND


def erase(openocd, erase_type: EraseType = EraseType.CHIP_ERASE, sectors: List[int] = []):
    if erase_type == EraseType.CHIP_ERASE:
        write_enable(openocd)
        chip_erase(openocd)
        wait_busy(openocd)
    elif erase_type == EraseType.SECTOR_ERASE:
        for sector in sectors:
            write_enable(openocd)
            sector_erase(openocd, sector)
            wait_busy(openocd)


def quad_page_program(
    openocd: OpenOcdTclRpc,
    ByteAddress: int,
    data: List[int],
    byte_count: int,
    progress: str = "",
    dma: Union[dma.DMA, None] = None
):
    print(f"Writing page {ByteAddress:#010x}... {progress}", flush=True)
    if byte_count > 256:
        raise FlashError("Byte count more than 256")

    write_enable(openocd)
    spifi.send_command(openocd, QUAD_PAGE_PROGRAM_COMMAND, spifi.Frameform.OPCODE_3ADDR,
                       spifi.Fieldform.DATA_PARALLEL, byte_count=byte_count, address=ByteAddress,
                       idata=0, cache_limit=0, direction=spifi.Direction.WRITE, data=data, dma=dma)
    wait_busy(openocd)


def quad_enable(openocd):
    if (check_quad_enable(openocd) != True):
        write_sreg(
            openocd, 
            read_sreg(openocd, SREG_Num.SREG1), 
            read_sreg(openocd, SREG_Num.SREG2) | SREG2_QUAD_ENABLE_M
        )


def check_quad_enable(openocd):
    return (read_sreg(openocd, SREG_Num.SREG2) & SREG2_QUAD_ENABLE_M) != 0
