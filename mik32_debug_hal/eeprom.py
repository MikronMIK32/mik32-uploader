import datetime
from enum import Enum
import os
import pathlib
import sys
from typing import Dict, List, Tuple
import time
from tclrpc import OpenOcdTclRpc
from utils import bytes2words

import mik32_debug_hal.registers.memory_map as mem_map
import mik32_debug_hal.registers.bitfields.eeprom as eeprom_fields


def eeprom_sysinit(openocd: OpenOcdTclRpc):
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


def eeprom_execute_operation(openocd: OpenOcdTclRpc, op: EEPROM_Operation, affected_pages: EEPROM_AffectedPages, offset: int, buffer: List[int]):
    # buffer write enable and select affected pages
    openocd.write_memory(mem_map.EEPROM_REGS_EEA, 32, [offset, (1 << eeprom_fields.EECON_BWE_S)
                                                       | (affected_pages.value << eeprom_fields.EECON_WRBEH_S)])

    if buffer.__len__() > 32:
        return
    for word in buffer:
        openocd.write_word(mem_map.EEPROM_REGS_EEDAT, word)
    # start operation
    openocd.write_word(mem_map.EEPROM_REGS_EECON, (
        (1 << eeprom_fields.EECON_EX_S) | (1 << eeprom_fields.EECON_BWE_S) |
        (op.value << eeprom_fields.EECON_OP_S) | (
            affected_pages.value << eeprom_fields.EECON_WRBEH_S)
    ))


def eeprom_configure_cycles(openocd: OpenOcdTclRpc, LD=1, R_1=2, R_2=1, CYCEP1=66667, CYCEP2=500):
    openocd.write_word(mem_map.EEPROM_REGS_NCYCRL, LD << eeprom_fields.NCYCRL_N_LD_S |
                       R_1 << eeprom_fields.NCYCRL_N_R_1_S | R_2 << eeprom_fields.NCYCRL_N_R_2_S)
    openocd.write_word(mem_map.EEPROM_REGS_NCYCEP1, CYCEP1)
    openocd.write_word(mem_map.EEPROM_REGS_NCYCEP2, CYCEP2)


def eeprom_global_erase(openocd: OpenOcdTclRpc):
    print("EEPROM global erase...", flush=True)
    # configure cycles duration
    eeprom_execute_operation(
        openocd, EEPROM_Operation.ERASE, EEPROM_AffectedPages.GLOBAL, 0x0, [0] * 32)


def eeprom_global_erase_check(openocd: OpenOcdTclRpc):
    print("EEPROM global erase check through APB...", flush=True)
    print("  Read Data at ...", flush=True)
    ex_value = 0x00000000
    openocd.write_word(mem_map.EEPROM_REGS_EEA, 0x00000000)
    for i in range(0, 64):
        print(f"    Row={i+1}/64")
        for j in range(0, 32):
            value = openocd.read_memory(mem_map.EEPROM_REGS_EEDAT, 32, 1)[0]
            if ex_value != value:
                print(
                    f"Unexpect value at Row {i}, Word {j}, expect {ex_value:#0x}, {value:#0x}", flush=True)


def eeprom_write_word(openocd: OpenOcdTclRpc, address: int, word: int):
    eeprom_execute_operation(
        openocd, EEPROM_Operation.PROGRAM, EEPROM_AffectedPages.SINGLE, address, [word])
    time.sleep(0.001)


def eeprom_write_page(openocd: OpenOcdTclRpc, address: int, data: List[int]):
    eeprom_execute_operation(
        openocd, EEPROM_Operation.PROGRAM, EEPROM_AffectedPages.SINGLE, address, data)
    time.sleep(0.001)


def eeprom_check_data_apb(openocd: OpenOcdTclRpc, words: List[int], offset: int, print_progress=True) -> int:
    if print_progress:
        print("EEPROM check through APB...", flush=True)
    # address load
    openocd.write_word(mem_map.EEPROM_REGS_EEA, offset)
    word_num = 0
    progress = 0
    if print_progress:
        print("[", end="", flush=True)
    for word in words:
        value: int = openocd.read_word(mem_map.EEPROM_REGS_EEDAT)
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


def eeprom_check_data_ahb_lite(openocd: OpenOcdTclRpc, words: List[int], offset: int, print_progress=True) -> int:
    if print_progress:
        print("EEPROM check through AHB-Lite...", flush=True)
    mem_array = openocd.read_memory(0x01000000 + offset, 32, len(words))
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


def eeprom_check_data(openocd: OpenOcdTclRpc, words: List[int], offset: int, print_progress=True, read_through_apb=False) -> int:
    if read_through_apb:
        return eeprom_check_data_apb(openocd, words, offset, print_progress)
    else:
        return eeprom_check_data_ahb_lite(openocd, words, offset, print_progress)


def write_words(words: List[int], openocd: OpenOcdTclRpc, write_by_word=False, read_through_apb=False) -> int:
    """
    Write words in MIK32 EEPROM through APB bus

    @words: list of words to write at offset 0x0
    @write_by_word: if True, write every word in separete page flash operation
    @read_through_apb: if True, check written words through APB instead of AHB-Lite

    TODO: implement setting byte array offset, add error handling, 
    improve progress visualization, add option check page immidiately after writing

    @return: return 0 if successful, 1 if failed
    """
    print(f"Write {len(words*4)} bytes", flush=True)

    openocd.halt()
    eeprom_sysinit(openocd)
    eeprom_global_erase(openocd)
    # eeprom_global_erase_check(openocd)
    # configure cycles duration
    eeprom_configure_cycles(openocd, 1, 3, 1, 100000, 1000)
    time.sleep(0.1)
    word_num: int = 0
    progress: int = 0
    print("EEPROM writing...", flush=True)
    print("[", end="", flush=True)
    if write_by_word:
        for word in words:
            eeprom_write_word(openocd, word_num*4, word)
            word_num += 1
            curr_progress = int((word_num * 50) / len(words))
            if curr_progress > progress:
                print("#"*(curr_progress - progress), end="", flush=True)
                progress = curr_progress
    else:
        page = []
        page_num = 0
        page_size = 32
        while word_num < len(words):
            if word_num < page_size*(page_num+1):
                page.append(words[word_num])
                word_num += 1
            else:
                # print(list(map(lambda word: f"{word:#0x}", page)))
                eeprom_write_page(openocd, page_num*page_size*4, page)
                page_num += 1
                page.clear()
            curr_progress = int((word_num * 50) / len(words))
            if curr_progress > progress:
                print("#"*(curr_progress - progress), end="", flush=True)
                progress = curr_progress
        eeprom_write_page(openocd, page_num*page_size*4, page)
    print("]", flush=True)
    if read_through_apb:
        result = eeprom_check_data_apb(openocd, words, 0)
    else:
        result = eeprom_check_data_ahb_lite(openocd, words, 0)

    if result == 0:
        print("EEPROM write file done!", flush=True)
    return result


def check_pages(pages: Dict[int, List[int]], openocd: OpenOcdTclRpc) -> int:
    openocd.halt()
    eeprom_sysinit(openocd)
    # configure cycles duration
    eeprom_configure_cycles(openocd, 1, 3, 1, 100000, 1000)
    time.sleep(0.1)
    print("EEPROM checking...", flush=True)

    pages_offsets = list(pages)

    for index, page_offset in enumerate(pages_offsets):
        page_words = bytes2words(pages[page_offset])

        print(
            f"Check page {page_offset:#06x}... {(index*100)//pages_offsets.__len__()}%", flush=True)

        if eeprom_check_data(openocd, page_words, page_offset, False):
            print("Page mismatch!", flush=True)
            return 1

    print("EEPROM page check completed", flush=True)
    return 0


def write_pages(pages: Dict[int, List[int]], openocd: OpenOcdTclRpc) -> int:
    openocd.halt()
    eeprom_sysinit(openocd)
    eeprom_global_erase(openocd)
    if eeprom_check_data_ahb_lite(openocd, [0]*2048, 0, False):
        print("EEPROM global erase failed, try again", flush=True)
        eeprom_global_erase(openocd)

        if eeprom_check_data_ahb_lite(openocd, [0]*2048, 0, False):
            print("EEPROM global erase failed", flush=True)
            return 1
    # configure cycles duration
    eeprom_configure_cycles(openocd, 1, 3, 1, 100000, 1000)
    time.sleep(0.1)
    print("EEPROM writing...", flush=True)

    pages_offsets = list(pages)

    for index, page_offset in enumerate(pages_offsets):
        page_words = bytes2words(pages[page_offset])

        print(
            f"Writing page {page_offset:#06x}... {(index*100)//pages_offsets.__len__()}%", flush=True)
        eeprom_write_page(openocd, page_offset, page_words)

        if eeprom_check_data(openocd, page_words, page_offset, False):
            print("Page mismatch!", flush=True)
            return 1

    print("EEPROM page recording completed", flush=True)
    return 0


def wait_halted(openocd: OpenOcdTclRpc, timeout_seconds: float = 2):
    openocd.run(f'wait_halt {int(timeout_seconds * 1000)}')


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


def write_memory(pages: Dict[int, List[int]], openocd: OpenOcdTclRpc, driver_path: str) -> int:
    """
    Записать всю память с использованием драйвера.

    pages: Dict[int, List[int]] -- страница - список байт, ключ - адрес в EEPROM
    """

    # TODO: добавить проверку на версию mik32 - текущий драйвер поддерживает
    # только версию mik32v2

    bytes_list = combine_pages(pages)
    openocd.halt()
    openocd.run("riscv.cpu set_reg {mstatus 0 mie 0}") # Отключение прерываний

    STATUS_CODE_M = 0xFF

    max_address = len(bytes_list) // 128
    openocd.write_memory(0x02003800, 32, [1 | (max_address << 8)])

    pathname = os.path.dirname(sys.argv[0])
    openocd.run("wp 0x2003800 4 w")  # готовимся поймать результат записи

    print("Uploading driver... ", end="", flush=True)
    openocd.run(f"load_image {{{pathlib.Path(driver_path)}}}")
    print("OK!", flush=True)

    print("Uploading data...   ", end="", flush=True)
    openocd.write_memory(0x02001800, 8, bytes_list)
    print("OK!", flush=True)

    print("Run driver...", flush=True)
    openocd.resume(0x2000000)

    wait_halted(openocd, 10)        # ждем, когда watchpoint сработает
    openocd.run("rwp 0x02003800")   # watchpoint ловит до изменения слова
    openocd.run("step")             # делаем шаг, чтобы прочитать новое слово

    result = openocd.read_memory(0x2003800, 32, 1)[0]

    if (result & 0xFF) == 0:
        print(f"EEPROM writing successfully completed!", flush=True)
    else:
        miss_page = (result >> 8) & (64 - 1)
        miss_byte = (result >> 16) & (128 - 1)
        expected_byte = pages[miss_page*128][miss_byte]
        miss_byte = (result >> 24) & 0xFF

        print(f"EEPROM writing failed!", flush=True)
        print(f"First mismatched byte in page {miss_page},")
        print(f"byte {miss_byte}, expected {expected_byte}, read {miss_byte}")

        return 1

    return 0
