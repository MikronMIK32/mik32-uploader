from enum import Enum
import os
import pathlib
import sys
from typing import Dict, List
import time
from tclrpc import OpenOcdTclRpc, TclException
from utils import bytes2words

import mik32_debug_hal.registers.memory_map as mem_map
import mik32_debug_hal.registers.bitfields.eeprom as eeprom_fields


def combine_pages(pages: Dict[int, List[int]]) -> List[int]:
    """
    Объединить страницы в последовательность байт с заполнением промежутков
    """
    bytes_list: List[int] = []
    found_pages = 0
    for page in range(64):
        if found_pages == len(pages):
            break
        page = pages.get(page * 128)
        if page is not None:
            bytes_list.extend(page)
            found_pages += 1
        else:
            bytes_list.extend([0]*128)

    return bytes_list


class EEPROM():
    openocd: OpenOcdTclRpc

    def __init__(self, openocd: OpenOcdTclRpc):
        self.openocd = openocd

        self.eeprom_sysinit()

    def eeprom_sysinit(self):
        print("MCU clock init...", flush=True)

    class EEPROM_Operation(Enum):
        READ = eeprom_fields.OP_RD
        ERASE = eeprom_fields.OP_ER
        PROGRAM = eeprom_fields.OP_PR

    class EEPROM_AffectedPages(Enum):
        SINGLE = 0
        EVEN = eeprom_fields.BEH_EVEN
        ODD = eeprom_fields.BEH_ODD
        GLOBAL = eeprom_fields.BEH_GLOB

    def eeprom_execute_operation(self, op: EEPROM_Operation, affected_pages: EEPROM_AffectedPages, offset: int, buffer: List[int]):
        # buffer write enable and select affected pages
        self.openocd.write_memory(mem_map.EEPROM_REGS_EEA, 32, [offset, (1 << eeprom_fields.EECON_BWE_S)
                                                                | (affected_pages.value << eeprom_fields.EECON_WRBEH_S)])

        if buffer.__len__() > 32:
            return
        for word in buffer:
            self.openocd.write_word(mem_map.EEPROM_REGS_EEDAT, word)
        # start operation
        self.openocd.write_word(mem_map.EEPROM_REGS_EECON, (
            (1 << eeprom_fields.EECON_EX_S) | (1 << eeprom_fields.EECON_BWE_S) |
            (op.value << eeprom_fields.EECON_OP_S) | (
                affected_pages.value << eeprom_fields.EECON_WRBEH_S)
        ))

    def eeprom_configure_cycles(self, LD=1, R_1=2, R_2=1, CYCEP1=66667, CYCEP2=500):
        self.openocd.write_word(mem_map.EEPROM_REGS_NCYCRL, LD << eeprom_fields.NCYCRL_N_LD_S |
                                R_1 << eeprom_fields.NCYCRL_N_R_1_S | R_2 << eeprom_fields.NCYCRL_N_R_2_S)
        self.openocd.write_word(mem_map.EEPROM_REGS_NCYCEP1, CYCEP1)
        self.openocd.write_word(mem_map.EEPROM_REGS_NCYCEP2, CYCEP2)

    def eeprom_global_erase(self):
        print("EEPROM global erase...", flush=True)
        # configure cycles duration
        self.eeprom_execute_operation(
            self.EEPROM_Operation.ERASE, self.EEPROM_AffectedPages.GLOBAL, 0x0, [0] * 32)

    def eeprom_global_erase_check(self):
        print("EEPROM global erase check through APB...", flush=True)
        print("  Read Data at ...", flush=True)
        ex_value = 0x00000000
        self.openocd.write_word(mem_map.EEPROM_REGS_EEA, 0x00000000)
        for i in range(0, 64):
            print(f"    Row={i+1}/64")
            for j in range(0, 32):
                value = self.openocd.read_memory(
                    mem_map.EEPROM_REGS_EEDAT, 32, 1)[0]
                if ex_value != value:
                    print(
                        f"Unexpect value at Row {i}, Word {j}, expect {ex_value:#0x}, {value:#0x}", flush=True)

    def eeprom_write_word(self, address: int, word: int):
        self.eeprom_execute_operation(
            self.EEPROM_Operation.PROGRAM, self.EEPROM_AffectedPages.SINGLE, address, [word])
        time.sleep(0.001)

    def eeprom_write_page(self, address: int, data: List[int]):
        self.eeprom_execute_operation(
            self.EEPROM_Operation.PROGRAM, self.EEPROM_AffectedPages.SINGLE, address, data)
        time.sleep(0.001)

    def eeprom_check_data_apb(self, words: List[int], offset: int, print_progress=True) -> int:
        if print_progress:
            print("EEPROM check through APB...", flush=True)
        # address load
        self.openocd.write_word(mem_map.EEPROM_REGS_EEA, offset)
        word_num = 0
        progress = 0
        if print_progress:
            print("[", end="", flush=True)
        for word in words:
            value: int = self.openocd.read_word(mem_map.EEPROM_REGS_EEDAT)
            if words[word_num] != value:
                print(
                    f"Unexpect value at {word_num} word, expect {word:#0x}, get {value:#0x}", flush=True)
                return 1
            word_num += 1
            curr_progress = int((word_num * 50) / len(words))
            if print_progress and (curr_progress > progress):
                print("#"*(curr_progress - progress), end="", flush=True)
                progress = curr_progress
        if print_progress:
            print("]", flush=True)
            print("EEPROM check through APB done!", flush=True)
        return 0

    def eeprom_check_data_ahb_lite(self, words: List[int], offset: int, print_progress=True) -> int:
        if print_progress:
            print("EEPROM check through AHB-Lite...", flush=True)
        mem_array = self.openocd.read_memory(
            0x01000000 + offset, 32, len(words))
        if len(words) != len(mem_array):
            print("ERROR: Wrong number of words in read_memory output!")
            return 1
        progress = 0
        if print_progress:
            print("[", end="", flush=True)
        for word_num in range(len(words)):
            if words[word_num] != mem_array[word_num]:
                print(f"Unexpect value at {word_num} word, expect {words[word_num]:#0x}, "
                      f"get {mem_array[word_num]:#0x}", flush=True)
                return 1
            curr_progress = int((word_num * 50) / len(words))
            if print_progress and (curr_progress > progress):
                print("#"*(curr_progress - progress), end="", flush=True)
                progress = curr_progress
        if print_progress:
            print("]", flush=True)
            print("EEPROM check through APB done!", flush=True)
        return 0

    def eeprom_check_data(self, words: List[int], offset: int, print_progress=True, read_through_apb=False) -> int:
        if read_through_apb:
            return self.eeprom_check_data_apb(words, offset, print_progress)
        else:
            return self.eeprom_check_data_ahb_lite(words, offset, print_progress)

    def check_pages(self, pages: Dict[int, List[int]]) -> int:
        self.openocd.halt()
        self.eeprom_sysinit()
        # configure cycles duration
        self.eeprom_configure_cycles(1, 3, 1, 100000, 1000)
        time.sleep(0.1)
        print("EEPROM checking...", flush=True)

        pages_offsets = list(pages)

        for index, page_offset in enumerate(pages_offsets):
            page_words = bytes2words(pages[page_offset])

            print(
                f"Check page {page_offset:#06x}... {(index*100)//pages_offsets.__len__()}%", flush=True)

            if self.eeprom_check_data(page_words, page_offset, False):
                print("Page mismatch!", flush=True)
                return 1

        print("EEPROM page check completed", flush=True)
        return 0

    def write_pages(self, pages: Dict[int, List[int]]) -> int:
        self.openocd.halt()
        self.eeprom_sysinit()
        self.eeprom_global_erase()

        if self.eeprom_check_data_ahb_lite([0]*2048, 0, False):
            print("EEPROM global erase failed, try again", flush=True)
            self.eeprom_global_erase()

            if self.eeprom_check_data_ahb_lite([0]*2048, 0, False):
                print("EEPROM global erase failed", flush=True)
                return 1
            
        # configure cycles duration
        self.eeprom_configure_cycles(1, 3, 1, 100000, 1000)
        time.sleep(0.1)
        print("EEPROM writing...", flush=True)

        pages_offsets = list(pages)

        for index, page_offset in enumerate(pages_offsets):
            page_words = bytes2words(pages[page_offset])

            print(
                f"Writing page {page_offset:#06x}... {(index*100)//pages_offsets.__len__()}%", flush=True)
            self.eeprom_write_page(page_offset, page_words)

            if self.eeprom_check_data(page_words, page_offset, False):
                print("Page mismatch!", flush=True)
                return 1

        print("EEPROM page recording completed", flush=True)
        return 0

    def wait_halted(self, timeout_seconds: float = 2):
        self.openocd.run(f'wait_halt {int(timeout_seconds * 1000)}')

    def write_memory(self, pages: Dict[int, List[int]], driver_path: str) -> int:
        """
        Записать всю память с использованием драйвера.

        pages: Dict[int, List[int]] -- страница - список байт, ключ - адрес в EEPROM
        """

        # TODO: добавить проверку на версию mik32 - текущий драйвер поддерживает
        # только версию mik32v2

        RAM_OFFSET = 0x02000000
        RAM_BUFFER_OFFSET = 0x02001800
        RAM_DRIVER_STATUS = 0x02003800

        bytes_list = combine_pages(pages)
        self.openocd.halt()
        # Отключение прерываний
        self.openocd.run("riscv.cpu set_reg {mstatus 0 mie 0}")

        STATUS_CODE_M = 0xFF

        max_address = len(bytes_list) // 128
        self.openocd.write_memory(RAM_DRIVER_STATUS, 32, [
                                  1 | (max_address << 8)])

        pathname = os.path.dirname(sys.argv[0])

        print("Uploading driver... ", end="", flush=True)
        self.openocd.run(f"load_image {{{pathlib.Path(driver_path)}}}")
        print("OK!", flush=True)

        print("Uploading data...   ", end="", flush=True)
        result = self.openocd.write_memory(RAM_BUFFER_OFFSET, 8, bytes_list)
        if result:
            print("ERROR!", flush=True)
            print("An error occurred while writing data to the buffer area!")
            print("Aborting...", flush=True)
            return 1
        else:
            print("OK!", flush=True)

        # готовимся поймать результат записи
        self.openocd.run(f"wp 0x{RAM_DRIVER_STATUS:08x} 4 w")

        print("Run driver...", flush=True)
        self.openocd.resume(RAM_OFFSET)

        try:
            # ждем, когда watchpoint сработает
            self.wait_halted(10)
        except TclException:
            print("Timeout!", flush=True)
            # return 1

        # watchpoint ловит до изменения слова
        self.openocd.run(f"rwp 0x{RAM_DRIVER_STATUS:08x}")
        # делаем шаг, чтобы прочитать новое слово
        self.openocd.run("step")

        result = self.openocd.read_memory(RAM_DRIVER_STATUS, 32, 1)[0]

        if (result & STATUS_CODE_M) == 0:
            print(f"EEPROM writing successfully completed!", flush=True)
        else:
            miss_page = (result >> 8) & (64 - 1)
            miss_byte = (result >> 16) & (128 - 1)
            expected_byte = pages[miss_page*128][miss_byte]
            miss_byte = (result >> 24) & 0xFF

            print(f"EEPROM writing failed!", flush=True)
            print(f"First mismatched byte in page {miss_page},")
            print(
                f"byte {miss_byte}, expected {expected_byte}, read {miss_byte}")

            return 1

        return 0
