from enum import Enum
import os
import pathlib
import sys
import time
from typing import Dict, List, Union
from tclrpc import OpenOcdTclRpc
from mik32_debug_hal.spifi import SPIFI
# import mik32_debug_hal.spifi as spifi
import mik32_debug_hal.dma as dma


class GenericFlash():
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

    openocd: OpenOcdTclRpc
    spifi: SPIFI

    def __init__(self, spifi: SPIFI):
        self.spifi = spifi
        self.openocd = self.spifi.openocd

        # self.init()

    def write_enable(self):
        self.spifi.send_command(self.WRITE_ENABLE_COMMAND,
                                self.spifi.Frameform.OPCODE_NOADDR, self.spifi.Fieldform.ALL_SERIAL)

    def read_sreg(self, sreg: SREG_Num) -> int:
        return self.spifi.send_command(
            self.READ_SREG1_COMMAND | sreg.value,
            self.spifi.Frameform.OPCODE_NOADDR,
            self.spifi.Fieldform.ALL_SERIAL,
            byte_count=1
        )[0]

    def write_sreg(self, sreg1: int, sreg2: int):
        self.write_enable()
        self.spifi.send_command(
            self.WRITE_SREG_COMMAND,
            self.spifi.Frameform.OPCODE_NOADDR,
            self.spifi.Fieldform.ALL_SERIAL,
            byte_count=2,
            direction=self.spifi.Direction.WRITE,
            data=[sreg1, sreg2]
        )
        self.wait_busy()

    def wait_busy(self):
        while 1:
            sreg1 = self.read_sreg(self.SREG_Num.SREG1)
            if not (sreg1 & self.SREG1_BUSY):
                break

    RESET_DELAY = 0.001

    def chip_reset(self):
        self.spifi.send_command(self.ENABLE_RESET_COMMAND,
                                self.spifi.Frameform.OPCODE_NOADDR, self.spifi.Fieldform.ALL_SERIAL)
        self.spifi.send_command(self.RESET_COMMAND,
                                self.spifi.Frameform.OPCODE_NOADDR, self.spifi.Fieldform.ALL_SERIAL)
        time.sleep(self.RESET_DELAY)

    def chip_reset_qpi(self):
        self.spifi.send_command(self.ENABLE_RESET_COMMAND,
                                self.spifi.Frameform.OPCODE_NOADDR, self.spifi.Fieldform.ALL_PARALLEL)
        self.spifi.send_command(self.RESET_COMMAND,
                                self.spifi.Frameform.OPCODE_NOADDR, self.spifi.Fieldform.ALL_PARALLEL)
        time.sleep(self.RESET_DELAY)

    def chip_erase(self):
        print("Chip erase...", flush=True)
        self.spifi.send_command(self.CHIP_ERASE_COMMAND,
                                self.spifi.Frameform.OPCODE_NOADDR, self.spifi.Fieldform.ALL_SERIAL)

    def sector_erase(self, address: int):
        print(f"Erase sector {address:#010x}...", flush=True)
        self.spifi.send_command(self.SECTOR_ERASE_COMMAND,
                                self.spifi.Frameform.OPCODE_3ADDR, self.spifi.Fieldform.ALL_SERIAL, address=address)

    def read_data(self, address: int, byte_count: int, bin_data: List[int], dma: Union[dma.DMA, None] = None, use_quad_spi=False) -> int:
        read_data: List[int] = []

        if (use_quad_spi):
            read_data = self.spifi.send_command(self.FAST_READ_QUAD_OUTPUT_COMMAND, self.spifi.Frameform.OPCODE_3ADDR,
                                                self.spifi.Fieldform.DATA_PARALLEL, byte_count=byte_count, address=address, idata_length=1, dma=dma)
        else:
            read_data = self.spifi.send_command(self.READ_DATA_COMMAND, self.spifi.Frameform.OPCODE_3ADDR,
                                                self.spifi.Fieldform.ALL_SERIAL, byte_count=byte_count, address=address, dma=dma)

        for i in range(byte_count):
            if read_data[i] != bin_data[i]:
                print(
                    f"DATA[{i+address}] = {read_data[i]:#0x} expect {bin_data[i]:#0x}", flush=True)

                return 1

        return 0

    def page_program(
            self,
            ByteAddress: int,
            data: List[int],
            byte_count: int,
            progress: str = "",
            dma: Union[dma.DMA, None] = None
    ):
        print(
            f"Writing Flash page {ByteAddress:#010x}... {progress}", flush=True)
        if byte_count > 256:
            raise self.FlashError("Byte count more than 256")

        self.write_enable()
        self.spifi.send_command(self.PAGE_PROGRAM_COMMAND, self.spifi.Frameform.OPCODE_3ADDR,
                                self.spifi.Fieldform.ALL_SERIAL, byte_count=byte_count, address=ByteAddress,
                                idata=0, cache_limit=0, direction=self.spifi.Direction.WRITE, data=data, dma=dma)
        self.wait_busy()

    class EraseType(Enum):
        CHIP_ERASE = 0
        SECTOR_ERASE = 1

    def erase(self, erase_type: EraseType = EraseType.CHIP_ERASE, sectors: List[int] = []):
        if erase_type == self.EraseType.CHIP_ERASE:
            self.write_enable()
            self.chip_erase()
            self.wait_busy()
        elif erase_type == self.EraseType.SECTOR_ERASE:
            for sector in sectors:
                self.write_enable()
                self.sector_erase(sector)
                self.wait_busy()

    def quad_page_program(
        self,
        ByteAddress: int,
        data: List[int],
        byte_count: int,
        progress: str = "",
        dma: Union[dma.DMA, None] = None
    ):
        print(f"Writing page {ByteAddress:#010x}... {progress}", flush=True)
        if byte_count > 256:
            raise self.FlashError("Byte count more than 256")

        self.write_enable()
        self.spifi.send_command(self.QUAD_PAGE_PROGRAM_COMMAND, self.spifi.Frameform.OPCODE_3ADDR,
                                self.spifi.Fieldform.DATA_PARALLEL, byte_count=byte_count, address=ByteAddress,
                                idata=0, cache_limit=0, direction=self.spifi.Direction.WRITE, data=data, dma=dma)
        self.wait_busy()

    def quad_enable(self):
        if (self.check_quad_enable(self.openocd) != True):
            self.write_sreg(
                self.read_sreg(self.SREG_Num.SREG1),
                self.read_sreg(self.SREG_Num.SREG2) | self.SREG2_QUAD_ENABLE_M
            )

    def check_quad_enable(self):
        return (self.read_sreg(self.SREG_Num.SREG2) & self.SREG2_QUAD_ENABLE_M) != 0

    def check_pages(self, pages: Dict[int, List[int]], use_quad_spi=False, use_chip_erase=False):
        result = 0

        self.openocd.halt()
        # self.init()

        # Сбрасываем микросхему в режиме QPI из всех состояний в нормальный SPI режим.
        self.chip_reset_qpi()

        # Сбрасываем микросхему в режиме SPI из всех состояний в нормальный SPI режим.
        self.chip_reset()

        JEDEC_ID = self.spifi.send_command(self.JEDEC_ID_COMMAND,
                                     self.spifi.Frameform.OPCODE_NOADDR, self.spifi.Fieldform.ALL_SERIAL, 3)

        print(
            f"JEDEC ID = {JEDEC_ID[0]:02x} {JEDEC_ID[1]:02x} {JEDEC_ID[2]:02x}")

        dma_instance = self.spifi.dma_config()

        if (use_quad_spi):
            print("Using Quad SPI")
            self.quad_enable(self.openocd)
        else:
            print("Using Single SPI")
        #    spifi_quad_disable(openocd)

        pages_offsets = list(pages)

        for index, page_offset in enumerate(pages_offsets):
            print(
                f"Check page {page_offset:#010x}... {(index*100)//pages_offsets.__len__()}%", flush=True)
            page_bytes = pages[page_offset]

            result = self.read_data(
                self.openocd, page_offset, 256, page_bytes, dma=dma_instance, use_quad_spi=use_quad_spi)

            if result == 1:
                print("Data error")
                # if (use_quad_spi):
                #    spifi_quad_disable(openocd)
                return result

        if result == 0:
            print("SPIFI pages checking completed", flush=True)
        return 0

    def write_pages(self, pages: Dict[int, List[int]], use_quad_spi=False, use_chip_erase=False):
        result = 0

        self.openocd.halt()
        # self.init()

        # Сбрасываем микросхему в режиме QPI из всех состояний в нормальный SPI режим.
        self.chip_reset_qpi()

        # Сбрасываем микросхему в режиме SPI из всех состояний в нормальный SPI режим.
        self.chip_reset()

        JEDEC_ID = self.spifi.send_command(self.JEDEC_ID_COMMAND,
                                     self.spifi.Frameform.OPCODE_NOADDR, self.spifi.Fieldform.ALL_SERIAL, 3)

        print(
            f"JEDEC ID = {JEDEC_ID[0]:02x} {JEDEC_ID[1]:02x} {JEDEC_ID[2]:02x}")

        dma_instance = self.spifi.dma_config()

        if use_chip_erase:
            self.erase(
                self.openocd, self.EraseType.CHIP_ERASE)
        else:
            self.erase(self.openocd, self.EraseType.SECTOR_ERASE,
                       self.get_segments_list(list(pages), 4*1024))

        print("Quad Enable", self.check_quad_enable(self.openocd))

        if (use_quad_spi):
            print("Using Quad SPI")
            self.quad_enable(self.openocd)
        else:
            print("Using Single SPI")
            # spifi_quad_disable(openocd)

        # print("SREG1", spifi_read_sreg(openocd, SREG_Num.SREG1))
        # print("SREG2", spifi_read_sreg(openocd, SREG_Num.SREG2))

        pages_offsets = list(pages)

        for index, page_offset in enumerate(pages_offsets):
            page_bytes = pages[page_offset]

            if (use_quad_spi):
                self.quad_page_program(
                    self.openocd, page_offset, page_bytes, 256, f"{(index*100)//pages_offsets.__len__()}%", dma=dma_instance)
            else:
                self.page_program(self.openocd, page_offset, page_bytes,
                                  256, f"{(index*100)//pages_offsets.__len__()}%", dma=dma_instance)

            result = self.read_data(
                self.openocd, page_offset, 256, page_bytes, dma=dma_instance, use_quad_spi=use_quad_spi)

            if result == 1:
                print("Data error")
                return result

        if result == 0:
            # Прошивка страниц флеш памяти по SPIFI была завершена
            print(
                "Flashing of flash memory pages via SPIFI has been completed", flush=True)
        return 0

    def wait_halted(self, timeout_seconds: float = 2):
        self.openocd.run(f'wait_halt {int(timeout_seconds * 1000)}')

    def write_pages_by_sectors(self, pages: Dict[int, List[int]],
                               driver_path: str,
                               use_quad_spi=False,
                               use_chip_erase=False,
                               ):
        result = 0

        self.openocd.halt()
        # Отключение прерываний
        self.openocd.run("riscv.cpu set_reg {mstatus 0 mie 0}")

        # self.init()
        # openocd.run("rwp")

        # Сбрасываем микросхему в режиме QPI из всех состояний в нормальный SPI режим.
        self.chip_reset_qpi()

        # Сбрасываем микросхему в режиме SPI из всех состояний в нормальный SPI режим.
        self.chip_reset()

        JEDEC_ID = self.spifi.send_command(
            0x9F, self.spifi.Frameform.OPCODE_NOADDR, self.spifi.Fieldform.ALL_SERIAL, 3)
        print(
            f"JEDEC_ID {JEDEC_ID[0]:02x} {JEDEC_ID[1]:02x} {JEDEC_ID[2]:02x}")

        sectors_list = self.get_segments_list(list(pages), 4*1024)

        self.openocd.halt()
        pathname = os.path.dirname(sys.argv[0])

        self.openocd.run("wp 0x2003000 4 w")

        print("Uploading driver... ", end="", flush=True)
        self.openocd.run(f"load_image {{{pathlib.Path(driver_path)}}}")
        print("OK!", flush=True)

        self.openocd.resume(0x2000000)
        self.wait_halted()

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

            result = self.openocd.write_memory(0x02002000, 8, bytes_list)
            if result:
                print("ERROR!", flush=True)
                print("An error occurred while writing data to the buffer area!")
                print("Aborting...", flush=True)
                return 1

            self.openocd.run(f"set_reg {{t6 {sector}}}")
            self.openocd.resume()
            self.wait_halted(10)    # ждем, когда watchpoint сработает
            # watchpoint ловит до изменения слова
            # делаем шаг, чтобы прочитать новое слово
            self.openocd.run("step")

            result = self.openocd.read_memory(0x2003000, 32, 1)[0]

            if result == 0:
                print(" OK!", flush=True)
            else:
                print(" FAIL!", flush=True)
                print("result =", result)
                break
        if result == 0:
            print(f"  {sectors_list[-1]:#010x} 100% OK!", flush=True)

        self.openocd.run("rwp 0x02003000")
        self.spifi.init_memory()

        if result == 0:
            # Прошивка страниц флеш памяти по SPIFI была завершена
            print("SPIFI writing successfully completed!", flush=True)
        else:
            print(f"SPIFI writing failed!", flush=True)
            return 1

        return result

    def write(self, address: int, data: List[int], data_len: int):
        if data_len > 256:
            raise self.SpifiError("Byte count more than 256")

        self.page_program(self.openocd, address, data, data_len)

        print("written")

    def write_file(self, bytes: List[int]):
        # print(bytes)
        print(f"Write {len(bytes)} bytes")

        self.openocd.halt()
        # self.init()
        self.erase()
        print("bin_data_len = ", len(bytes))
        address = 0

        for address in range(0, len(bytes), 256):
            if ((address + 256) > len(bytes)):
                break
            print("address = ", address)
            self.write(address, bytes, 256)
            if self.read_data(address, 256, bytes) == 1:
                return 1

        if (len(bytes) % 256) != 0:
            print(
                f"address = {address}, +{len(bytes) - address-1}[{address + len(bytes) - address-1}]")
            self.write(address, bytes, len(bytes) - address)
            if self.read_data(address, len(bytes) - address, bytes) == 1:
                return 1
        print("end")

        return 0

    def get_segments_list(self, pages_offsets: List[int], segment_size: int) -> List[int]:
        segments = set()
        for offset in pages_offsets:
            segments.add(offset & ~(segment_size - 1))
        return sorted(list(segments))
