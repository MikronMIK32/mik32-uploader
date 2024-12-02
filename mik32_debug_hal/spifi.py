import datetime
from enum import Enum
import os
import pathlib
import sys
from typing import Dict, List, Union
import time
from tclrpc import TclException
from tclrpc import OpenOcdTclRpc
import mik32_debug_hal.registers.memory_map as mem_map
import mik32_debug_hal.registers.bitfields.spifi as spifi_fields
import mik32_debug_hal.dma as dma
import flash_drivers.generic_flash as generic_flash


class SpifiError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return ("ERROR: " + repr(self.value))


def spifi_intrq_clear(openocd: OpenOcdTclRpc):
    openocd.write_word(mem_map.SPIFI_CONFIG_STAT, openocd.read_word(mem_map.SPIFI_CONFIG_STAT) |
                       spifi_fields.SPIFI_CONFIG_STAT_INTRQ_M)


INIT_DELAY = 0.001

TIMEOUT = 1.0


def init_periphery(openocd: OpenOcdTclRpc):
    openocd.write_word(mem_map.SPIFI_CONFIG_STAT, openocd.read_word(mem_map.SPIFI_CONFIG_STAT) |
                       #    SPIFI_CONFIG_STAT_INTRQ_M |
                       spifi_fields.SPIFI_CONFIG_STAT_RESET_M)
    # openocd.write_word(SPIFI_CONFIG_CTRL, openocd.read_word(
    #     SPIFI_CONFIG_CTRL) | (7 << SPIFI_CONFIG_CTRL_SCK_DIV_S))
    openocd.write_word(mem_map.SPIFI_CONFIG_ADDR, 0x00)
    openocd.write_word(mem_map.SPIFI_CONFIG_IDATA, 0x00)
    openocd.write_word(mem_map.SPIFI_CONFIG_CLIMIT, 0x00)

    time.sleep(INIT_DELAY)


def init(openocd: OpenOcdTclRpc):
    print("MCU clock init", flush=True)

    init_periphery(openocd)

    control = openocd.read_word(mem_map.SPIFI_CONFIG_CTRL)
    control |= spifi_fields.SPIFI_CONFIG_CTRL_DMAEN_M
    openocd.write_word(mem_map.SPIFI_CONFIG_CTRL, control)

    time.sleep(INIT_DELAY)


def init_memory(openocd: OpenOcdTclRpc):
    openocd.write_word(mem_map.SPIFI_CONFIG_STAT, openocd.read_word(mem_map.SPIFI_CONFIG_STAT) |
                       spifi_fields.SPIFI_CONFIG_STAT_INTRQ_M |
                       spifi_fields.SPIFI_CONFIG_STAT_RESET_M)
    # openocd.write_word(SPIFI_CONFIG_CTRL, openocd.read_word(
    #     SPIFI_CONFIG_CTRL) | (7 << SPIFI_CONFIG_CTRL_SCK_DIV_S))
    openocd.write_word(mem_map.SPIFI_CONFIG_ADDR, 0x00)
    openocd.write_word(mem_map.SPIFI_CONFIG_IDATA, 0x00)
    openocd.write_word(mem_map.SPIFI_CONFIG_CLIMIT, 0x00)
    openocd.write_word(mem_map.SPIFI_CONFIG_MCMD, (0 << spifi_fields.SPIFI_CONFIG_MCMD_INTLEN_S) |
                       (spifi_fields.SPIFI_CONFIG_CMD_FIELDFORM_ALL_SERIAL << spifi_fields.SPIFI_CONFIG_MCMD_FIELDFORM_S) |
                       (spifi_fields.SPIFI_CONFIG_CMD_FRAMEFORM_OPCODE_3ADDR << spifi_fields.SPIFI_CONFIG_MCMD_FRAMEFORM_S) |
                       (generic_flash.READ_DATA_COMMAND << spifi_fields.SPIFI_CONFIG_MCMD_OPCODE_S))

    time.sleep(INIT_DELAY)


def spifi_wait_intrq_timeout(openocd: OpenOcdTclRpc, error_message: str):
    time_end = time.perf_counter() + TIMEOUT
    while time.perf_counter() < time_end:
        if (openocd.read_word(mem_map.SPIFI_CONFIG_STAT) & spifi_fields.SPIFI_CONFIG_STAT_INTRQ_M) != 0:
            return
    raise SpifiError(error_message)


class Frameform(Enum):
    RESERVED = 0
    OPCODE_NOADDR = 1
    OPCODE_1ADDR = 2
    OPCODE_2ADDR = 3
    OPCODE_3ADDR = 4
    OPCODE_4ADDR = 5
    NOOPCODE_3ADDR = 6
    NOOPCODE_4ADDR = 7


class Fieldform(Enum):
    ALL_SERIAL = 0
    DATA_PARALLEL = 1
    OPCODE_SERIAL = 2
    ALL_PARALLEL = 3


class Direction(Enum):
    READ = 0
    WRITE = 1


def send_command(
        openocd: OpenOcdTclRpc,
        cmd: int,
        frameform: Frameform,
        fieldform: Fieldform,
        byte_count=0,
        address=0,
        idata=0,
        cache_limit=0,
        idata_length=0,
        direction=Direction.READ,
        data: List[int] = [],
        dma: Union[dma.DMA, None] = None
) -> List[int]:
    if (dma is not None) and (direction == Direction.WRITE):
        openocd.write_memory(0x02003F00, 8, data)

        dma.channels[0].start(
            0x02003F00,
            mem_map.SPIFI_CONFIG_DATA32,
            255
        )
    elif (dma is not None) and (direction == Direction.READ):
        dma.channels[1].start(
            mem_map.SPIFI_CONFIG_DATA32,
            0x02003F00,
            255
        )

    openocd.write_memory(mem_map.SPIFI_CONFIG_ADDR, 32, [address, idata])

    cmd_write_value = ((cmd << spifi_fields.SPIFI_CONFIG_CMD_OPCODE_S) |
                       (frameform.value << spifi_fields.SPIFI_CONFIG_CMD_FRAMEFORM_S) |
                       (fieldform.value << spifi_fields.SPIFI_CONFIG_CMD_FIELDFORM_S) |
                       (byte_count << spifi_fields.SPIFI_CONFIG_CMD_DATALEN_S) |
                       (idata_length << spifi_fields.SPIFI_CONFIG_CMD_INTLEN_S) |
                       (direction.value << spifi_fields.SPIFI_CONFIG_CMD_DOUT_S))

    openocd.write_memory(mem_map.SPIFI_CONFIG_CMD, 32, [cmd_write_value])

    if direction == Direction.READ:
        out_list = []
        if dma is not None:
            dma.dma_wait(dma.channels[1], 0.1)
            out_list.extend(openocd.read_memory(0x02003F00, 8, byte_count))

            return out_list
        else:
            for i in range(byte_count):
                out_list.append(openocd.read_memory(
                    mem_map.SPIFI_CONFIG_DATA32, 8, 1)[0])
            return out_list

    if direction == Direction.WRITE:
        if dma is not None:
            dma.dma_wait(dma.channels[0], 0.1)
        else:
            if (byte_count % 4) == 0:
                for i in range(0, byte_count, 4):
                    openocd.write_memory(mem_map.SPIFI_CONFIG_DATA32, 32, [
                        data[i] + data[i+1] * 256 + data[i+2] * 256 * 256 + data[i+3] * 256 * 256 * 256])
            else:
                for i in range(byte_count):
                    openocd.write_memory(
                        mem_map.SPIFI_CONFIG_DATA32, 8, [data[i]])

    return []


def write(openocd: OpenOcdTclRpc, address: int, data: List[int], data_len: int):
    if data_len > 256:
        raise SpifiError("Byte count more than 256")

    generic_flash.page_program(openocd, address, data, data_len)

    print("written")


def write_file(bytes: List[int], openocd: OpenOcdTclRpc):
    # print(bytes)
    print(f"Write {len(bytes)} bytes")

    openocd.halt()
    init(openocd)
    generic_flash.erase(openocd)
    print("bin_data_len = ", len(bytes))
    address = 0

    for address in range(0, len(bytes), 256):
        if ((address + 256) > len(bytes)):
            break
        print("address = ", address)
        write(openocd, address, bytes, 256)
        if generic_flash.read_data(openocd, address, 256, bytes) == 1:
            return 1

    if (len(bytes) % 256) != 0:
        print(
            f"address = {address}, +{len(bytes) - address-1}[{address + len(bytes) - address-1}]")
        write(openocd, address, bytes, len(bytes) - address)
        if generic_flash.read_data(openocd, address, len(bytes) - address, bytes) == 1:
            return 1
    print("end")

    return 0


def get_segments_list(pages_offsets: List[int], segment_size: int) -> List[int]:
    segments = set()
    for offset in pages_offsets:
        segments.add(offset & ~(segment_size - 1))
    return sorted(list(segments))


def dma_config(openocd: OpenOcdTclRpc) -> dma.DMA:
    dma_instance = dma.DMA(openocd)
    dma_instance.init()

    dma_instance.channels[0].write_buffer = 0

    dma_instance.channels[0].channel = dma.ChannelIndex.CHANNEL_0
    dma_instance.channels[0].priority = dma.ChannelPriority.VERY_HIGH

    dma_instance.channels[0].read_mode = dma.ChannelMode.MEMORY
    dma_instance.channels[0].read_increment = dma.ChannelIncrement.ENABLE
    dma_instance.channels[0].read_size = dma.ChannelSize.WORD
    dma_instance.channels[0].read_burst_size = 2
    dma_instance.channels[0].read_request = dma.ChannelRequest.SPIFI_REQUEST
    dma_instance.channels[0].read_ack = dma.ChannelAck.DISABLE

    dma_instance.channels[0].write_mode = dma.ChannelMode.PERIPHERY
    dma_instance.channels[0].write_increment = dma.ChannelIncrement.DISABLE
    dma_instance.channels[0].write_size = dma.ChannelSize.WORD
    dma_instance.channels[0].write_burst_size = 2
    dma_instance.channels[0].write_request = dma.ChannelRequest.SPIFI_REQUEST
    dma_instance.channels[0].write_ack = dma.ChannelAck.DISABLE

    dma_instance.channels[1].write_buffer = 0

    dma_instance.channels[1].channel = dma.ChannelIndex.CHANNEL_1
    dma_instance.channels[1].priority = dma.ChannelPriority.VERY_HIGH

    dma_instance.channels[1].write_mode = dma.ChannelMode.MEMORY
    dma_instance.channels[1].write_increment = dma.ChannelIncrement.ENABLE
    dma_instance.channels[1].write_size = dma.ChannelSize.WORD
    dma_instance.channels[1].write_burst_size = 2
    dma_instance.channels[1].write_request = dma.ChannelRequest.SPIFI_REQUEST
    dma_instance.channels[1].write_ack = dma.ChannelAck.DISABLE

    dma_instance.channels[1].read_mode = dma.ChannelMode.PERIPHERY
    dma_instance.channels[1].read_increment = dma.ChannelIncrement.DISABLE
    dma_instance.channels[1].read_size = dma.ChannelSize.WORD
    dma_instance.channels[1].read_burst_size = 2
    dma_instance.channels[1].read_request = dma.ChannelRequest.SPIFI_REQUEST
    dma_instance.channels[1].read_ack = dma.ChannelAck.DISABLE

    return dma_instance


def check_pages(pages: Dict[int, List[int]], openocd: OpenOcdTclRpc, use_quad_spi=False, use_chip_erase=False):
    result = 0

    openocd.halt()
    init(openocd)

    # Сбрасываем микросхему в режиме QPI из всех состояний в нормальный SPI режим.
    generic_flash.chip_reset_qpi(openocd)

    # Сбрасываем микросхему в режиме SPI из всех состояний в нормальный SPI режим.
    generic_flash.chip_reset(openocd)

    JEDEC_ID = send_command(openocd, generic_flash.JEDEC_ID_COMMAND,
                            Frameform.OPCODE_NOADDR, Fieldform.ALL_SERIAL, 3)

    print(f"JEDEC ID = {JEDEC_ID[0]:02x} {JEDEC_ID[1]:02x} {JEDEC_ID[2]:02x}")

    dma_instance = dma_config(openocd)

    if (use_quad_spi):
        print("Using Quad SPI")
        generic_flash.quad_enable(openocd)
    else:
        print("Using Single SPI")
    #    spifi_quad_disable(openocd)

    pages_offsets = list(pages)

    for index, page_offset in enumerate(pages_offsets):
        print(
            f"Check page {page_offset:#010x}... {(index*100)//pages_offsets.__len__()}%", flush=True)
        page_bytes = pages[page_offset]

        result = generic_flash.read_data(
            openocd, page_offset, 256, page_bytes, dma=dma_instance, use_quad_spi=use_quad_spi)

        if result == 1:
            print("Data error")
            # if (use_quad_spi):
            #    spifi_quad_disable(openocd)
            return result

    if result == 0:
        print("SPIFI pages checking completed", flush=True)
    return 0


def write_pages(pages: Dict[int, List[int]], openocd: OpenOcdTclRpc, use_quad_spi=False, use_chip_erase=False):
    result = 0

    openocd.halt()
    init(openocd)

    # Сбрасываем микросхему в режиме QPI из всех состояний в нормальный SPI режим.
    generic_flash.chip_reset_qpi(openocd)

    # Сбрасываем микросхему в режиме SPI из всех состояний в нормальный SPI режим.
    generic_flash.chip_reset(openocd)

    JEDEC_ID = send_command(openocd, generic_flash.JEDEC_ID_COMMAND,
                            Frameform.OPCODE_NOADDR, Fieldform.ALL_SERIAL, 3)

    print(f"JEDEC ID = {JEDEC_ID[0]:02x} {JEDEC_ID[1]:02x} {JEDEC_ID[2]:02x}")

    dma_instance = dma_config(openocd)

    if use_chip_erase:
        generic_flash.erase(openocd, generic_flash.EraseType.CHIP_ERASE)
    else:
        generic_flash.erase(openocd, generic_flash.EraseType.SECTOR_ERASE,
                            get_segments_list(list(pages), 4*1024))

    print("Quad Enable", generic_flash.check_quad_enable(openocd))

    if (use_quad_spi):
        print("Using Quad SPI")
        generic_flash.quad_enable(openocd)
    else:
        print("Using Single SPI")
        # spifi_quad_disable(openocd)

    # print("SREG1", spifi_read_sreg(openocd, SREG_Num.SREG1))
    # print("SREG2", spifi_read_sreg(openocd, SREG_Num.SREG2))

    pages_offsets = list(pages)

    for index, page_offset in enumerate(pages_offsets):
        page_bytes = pages[page_offset]

        if (use_quad_spi):
            generic_flash.quad_page_program(
                openocd, page_offset, page_bytes, 256, f"{(index*100)//pages_offsets.__len__()}%", dma=dma_instance)
        else:
            generic_flash.page_program(openocd, page_offset, page_bytes,
                                       256, f"{(index*100)//pages_offsets.__len__()}%", dma=dma_instance)

        result = generic_flash.read_data(
            openocd, page_offset, 256, page_bytes, dma=dma_instance, use_quad_spi=use_quad_spi)

        if result == 1:
            print("Data error")
            return result

    if result == 0:
        # Прошивка страниц флеш памяти по SPIFI была завершена
        print("Flashing of flash memory pages via SPIFI has been completed", flush=True)
    return 0


def wait_halted(openocd: OpenOcdTclRpc, timeout_seconds: float = 2):
    openocd.run(f'wait_halt {int(timeout_seconds * 1000)}')


def write_pages_by_sectors(pages: Dict[int, List[int]],
                           openocd: OpenOcdTclRpc,
                           driver_path: str,
                           use_quad_spi=False,
                           use_chip_erase=False,
                           ):
    result = 0

    openocd.halt()
    openocd.run("riscv.cpu set_reg {mstatus 0 mie 0}") # Отключение прерываний
    
    init(openocd)
    # openocd.run("rwp")

    JEDEC_ID = send_command(
        openocd, 0x9F, Frameform.OPCODE_NOADDR, Fieldform.ALL_SERIAL, 3)
    print(f"JEDEC_ID {JEDEC_ID[0]:02x} {JEDEC_ID[1]:02x} {JEDEC_ID[2]:02x}")

    dma_instance = dma_config(openocd)

    sectors_list = get_segments_list(list(pages), 4*1024)

    openocd.halt()
    pathname = os.path.dirname(sys.argv[0])

    openocd.run("wp 0x2003000 4 w")

    print("Uploading driver... ", end="", flush=True)
    openocd.run(f"load_image {{{pathlib.Path(driver_path)}}}")
    print("OK!", flush=True)

    openocd.resume(0x2000000)
    wait_halted(openocd)

    print("Writing Flash by sectors...", flush=True)

    for i, sector in enumerate(sectors_list):
        ByteAddress = sector
        progress = f"{(i*100)//len(sectors_list)}%"
        print(f"  {ByteAddress:#010x} {progress:>4}", end="", flush=True)
        bytes_list: List[int] = []
        for page in range(16):
            page = pages.get(page * 256 + sector)
            if page is not None:
                bytes_list.extend(page)
            else:
                bytes_list.extend([0]*256)

        openocd.write_memory(0x02002000, 8, bytes_list)
        openocd.run(f"set_reg {{t6 {sector}}}")
        openocd.resume()
        wait_halted(openocd, 10)    # ждем, когда watchpoint сработает
                                    # watchpoint ловит до изменения слова
        openocd.run("step")         # делаем шаг, чтобы прочитать новое слово

        result = openocd.read_memory(0x2003000, 32, 1)[0]
        
        if result == 0:
            print(" OK!", flush=True)
        else:
            print(" FAIL!", flush=True)
            print("result =", result)
            break
    if result == 0:
        print(f"  {sectors_list[-1]:#010x} 100% OK!", flush=True)

    openocd.run("rwp 0x02003000")
    init_memory(openocd)

    if result == 0:
        # Прошивка страниц флеш памяти по SPIFI была завершена
        print("SPIFI writing successfully completed!", flush=True)
    else:
        print(f"SPIFI writing failed!", flush=True)
        return 1
    
    return result
