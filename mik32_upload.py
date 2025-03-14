import shlex
import argparse
import socket
import subprocess
import os
import time
from enum import Enum
from typing import List, Dict, NamedTuple, Union
from hex_parser import FirmwareFile, MemorySection, MemoryType, Segment
from tclrpc import OpenOcdTclRpc, TclException, TclPortError
from mik32_debug_hal.gpio import MIK32_Version, gpio_init, gpio_deinit
from mik32_debug_hal.eeprom import EEPROM
from mik32_debug_hal.spifi import SPIFI
from flash_drivers.generic_flash import GenericFlash
import mik32_debug_hal.ram as ram
import mik32_debug_hal.power_manager as power_manager
from _version import applicaton_version
from parsers import *
import logging
import sys
from pathlib import Path
from sys import exit

program_name = f'mik32-uploader-{applicaton_version}'

openocd_exec = "openocd"
if os.name == 'nt':
    openocd_exec = "openocd.exe"

default_openocd_host = '127.0.0.1'
openocd_exec_path = os.path.join("openocd", "bin", openocd_exec)
openocd_scripts_path = os.path.join("openocd-scripts")
openocd_interface_path = os.path.join("interface", "ftdi", "mikron-link.cfg")
openocd_target_path = os.path.join("target", "mik32.cfg")
default_post_action = "reset run"

default_drivers_path = os.path.dirname(os.path.realpath(__file__))
default_drivers_build_path = ''

if os.path.split(default_drivers_path)[-1] == '_internal':
    default_drivers_path = os.path.join(
        os.path.dirname(default_drivers_path),
        'upload-drivers'
    )
else:
    default_drivers_path = os.path.join(default_drivers_path, 'upload-drivers')
    default_drivers_build_path = os.path.join('.pio', 'build', 'mik32v2')


default_log_path = "/dev/null"
if os.name == 'nt':
    default_log_path = "nul"

adapter_default_speed = 500


memory_page_size = {
    MemoryType.EEPROM: 128,
    MemoryType.SPIFI: 256
}


class BootMode(Enum):
    UNDEFINED = 'undefined'
    EEPROM = 'eeprom'
    RAM = 'ram'
    SPIFI = 'spifi'

    def __str__(self):
        return self.value

    def to_memory_type(self) -> MemoryType:
        if self.value == 'eeprom':
            return MemoryType.EEPROM
        if self.value == 'ram':
            return MemoryType.RAM
        if self.value == 'spifi':
            return MemoryType.SPIFI

        return MemoryType.UNKNOWN


mik32_sections: List[MemorySection] = [
    MemorySection(MemoryType.BOOT, 0x0, 16 * 1024),
    MemorySection(MemoryType.EEPROM, 0x01000000, 8 * 1024),
    MemorySection(MemoryType.RAM, 0x02000000, 16 * 1024),
    MemorySection(MemoryType.SPIFI, 0x80000000, 8 * 1024 * 1024),
]


def fill_pages_from_segment(segment: Segment, page_size: int, pages: Dict[int, List[int]]):
    if segment.memory is None:
        return

    internal_offset = segment.offset - segment.memory.offset

    for i, byte in enumerate(segment.data):
        byte_offset = internal_offset + i
        page_n = byte_offset // page_size
        page_offset = page_n * page_size

        if (page_offset) not in pages.keys():
            pages[page_offset] = [0] * page_size

        pages[page_offset][byte_offset - page_offset] = byte


def segments_to_pages(segments: List[Segment], page_size: int) -> Dict[int, List[int]]:
    pages: Dict[int, List[int]] = {}

    for segment in segments:
        fill_pages_from_segment(segment, page_size, pages)

    return pages


class OpenOCDError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return f"ERROR: OpenOCD Startup Exception: {self.msg}"


def run_openocd(
    openocd_exec=openocd_exec_path,
    openocd_scripts=openocd_scripts_path,
    openocd_interface=openocd_interface_path,
    openocd_target=openocd_target_path,
    is_open_console=False
) -> subprocess.Popen:
    cmd = [openocd_exec, "-s", openocd_scripts,
           "-f", openocd_interface, "-f", openocd_target]

    if os.name == 'nt':
        creation_flags = subprocess.SW_HIDE
        if is_open_console:
            creation_flags |= subprocess.CREATE_NEW_CONSOLE

        proc = subprocess.Popen(
            cmd, creationflags=creation_flags)
    else:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)

    return proc


class Pages(NamedTuple):
    pages_eeprom: Dict[int, List[int]]
    pages_spifi: Dict[int, List[int]]


def filter_segments(segments: List[Segment], memory_type: MemoryType, boot_type: MemoryType = MemoryType.UNKNOWN) -> List[Segment]:
    return list(
        filter(
            lambda segment:
               (segment.memory is not None) and
               ((segment.memory.type == memory_type) or (
                   (segment.memory.type == MemoryType.BOOT) and
                   (boot_type == memory_type)
               )), segments
        )
    )


def form_pages(segments: List[Segment], boot_mode=BootMode.UNDEFINED) -> Pages:
    pages_eeprom = segments_to_pages(
        filter_segments(segments, MemoryType.EEPROM,
                        boot_mode.to_memory_type()),
        memory_page_size[MemoryType.EEPROM]
    )
    pages_spifi = segments_to_pages(
        filter_segments(segments, MemoryType.SPIFI,
                        boot_mode.to_memory_type()),
        memory_page_size[MemoryType.SPIFI]
    )

    return Pages(pages_eeprom, pages_spifi)


adapter_speed_not_supported = [
    "altera-usb-blaster",
    "start-link",
]


def upload_file(
        filename: str,
        host: str = '127.0.0.1',
        port: int = OpenOcdTclRpc.DEFAULT_PORT,
        is_run_openocd=False,
        use_quad_spi=False,
        openocd_exec=openocd_exec_path,
        openocd_scripts=openocd_scripts_path,
        openocd_interface=openocd_interface_path,
        openocd_target=openocd_target_path,
        adapter_speed=adapter_default_speed,
        is_open_console=False,
        boot_mode=BootMode.UNDEFINED,
        log_path=default_log_path,
        post_action=default_post_action,
        mik_version=MIK32_Version.MIK32V2,
        use_driver=True,
) -> int:
    """
    Запись прошивки в формате Intel HEX или бинарном в память MIK32.
    @filename: полный путь до файла прошивки
    @return: возвращает 0 в случае успеха, 1 - если прошивка неудачна
    """

    print(f"Using {mik_version.value}")

    result = 0

    if not os.path.exists(filename):
        print(f"ERROR: File {filename} does not exist")
        return 1

    try:
        file = FirmwareFile(filename, mik32_sections)
    except ParserError as e:
        print(e)
        return 1

    segments: List[Segment] = file.get_segments()
    pages: Pages = form_pages(segments, boot_mode)

    try:
        port = int(port)
    except ValueError:
        print("An integer argument --openocd-port was expected!")

    proc: Union[subprocess.Popen, None] = None
    if is_run_openocd:
        try:
            logging.debug("OpenOCD try start!")

            proc = run_openocd(openocd_exec, openocd_scripts,
                               openocd_interface, openocd_target, is_open_console)

            logging.debug("OpenOCD started!")

        except OSError as e:
            raise OpenOCDError(e)
    try:
        time.sleep(0.1)
        with OpenOcdTclRpc(host, port) as openocd:
            try:
                openocd.run(f"log_output \"{log_path}\"")
                openocd.run(f"debug_level 1")
                openocd.run("capture \"riscv.cpu curstate\"")
            except OSError as e:
                print("ERROR: Tcl port connection failed")
                print("Check connectivity and OpenOCD log")
                return 1
            
            if (all(openocd_interface.find(i) == -1 for i in adapter_speed_not_supported)):
                openocd.run(f"adapter speed {adapter_speed}")
            

            logging.debug("OpenOCD configured!")

            result = power_manager.pm_init(openocd)
            if result != 0:
                return 1

            logging.debug("PM configured!")

            if (pages.pages_eeprom.__len__() > 0):
                eeprom = EEPROM(openocd)
                
                start_time = time.perf_counter()

                if use_driver:
                    result |= eeprom.write_memory(
                        pages.pages_eeprom,
                        os.path.join(
                            default_drivers_path,
                            'jtag-eeprom',
                            default_drivers_build_path,
                            'firmware.hex'
                        )
                    )
                else:
                    result |= eeprom.write_pages(
                        pages.pages_eeprom
                    )

                write_time = time.perf_counter() - start_time
                write_size = pages.pages_eeprom.__len__(
                ) * memory_page_size[MemoryType.EEPROM]
                t = time.localtime()
                current_time = time.strftime("%H:%M:%S", t)
                if result == 0:
                    print(
                        f"[{current_time}] Wrote {write_size} bytes in {write_time:.2f} seconds (effective {(write_size/(write_time*1024)):.1f} kbyte/s)")
            if (pages.pages_spifi.__len__() > 0):
                gpio_init(openocd, mik_version)
                spifi = SPIFI(openocd)
                flash = GenericFlash(spifi)
                start_time = time.perf_counter()

                if use_driver:
                    result |= flash.write_pages_by_sectors(
                        pages.pages_spifi,
                        os.path.join(
                            default_drivers_path,
                            'jtag-spifi',
                            default_drivers_build_path,
                            'firmware.hex'
                        )
                    )
                else:
                    result |= flash.write_pages(
                        pages.pages_spifi,
                        openocd,
                        use_quad_spi=use_quad_spi
                    )

                write_time = time.perf_counter() - start_time
                write_size = pages.pages_spifi.__len__(
                ) * memory_page_size[MemoryType.SPIFI]
                t = time.localtime()
                current_time = time.strftime("%H:%M:%S", t)
                if result == 0:
                    print(
                        f"[{current_time}] Wrote {write_size} bytes in {write_time:.2f} seconds (effective {(write_size/(write_time*1024)):.1f} kbyte/s)")
                gpio_deinit(openocd, mik_version)

            segments_ram = list(filter(
                lambda segment: (segment.memory is not None) and (segment.memory.type == MemoryType.RAM), segments))
            if (segments_ram.__len__() > 0):
                ram.write_segments(segments_ram, openocd)
                result |= 0

            openocd.run(post_action)
    except ConnectionRefusedError:
        print("ERROR: The connection to OpenOCD is not established. Check the settings and connection of the debugger")
    except (OpenOCDError, TclPortError, TclException) as e:
        print(e)
        exit(1)
    except ConnectionResetError as e:
        print("ERROR: Tcl connection reset")
        print("Check OpenOCD log")
        print(e.strerror)
    finally:
        if proc is not None:
            proc.kill()

    return result


def createParser():
    parser = argparse.ArgumentParser(
        prog='mik32_upload.py',
        usage='python mik32_upload.py firmware_name.hex',
        description='''Скрипт предназначен для записи программы в ОЗУ, EEPROM и внешнюю flash память, 
        подключенную по интерфейсу SPIFI. Поддерживаемые форматы прошивок: *.hex, *.bin'''
    )
    parser.add_argument(
        'filepath',
        nargs='?',
        help='Путь к файлу прошивки'
    )
    parser.add_argument(
        '--run-openocd',
        dest='run_openocd',
        action='store_true',
        default=False,
        help='Запуск openocd при прошивке МК'
    )
    parser.add_argument(
        '--use-quad-spi',
        dest='use_quad_spi',
        action='store_true',
        default=False,
        help='Использование режима QuadSPI при программировании внешней флеш памяти'
    )
    parser.add_argument(
        '--openocd-host',
        dest='openocd_host',
        default=default_openocd_host,
        help=f"Адрес для подключения к openocd. По умолчанию: {default_openocd_host}"
    )
    parser.add_argument(
        '--openocd-port',
        dest='openocd_port',
        default=OpenOcdTclRpc.DEFAULT_PORT,
        help=f"Порт tcl сервера openocd. По умолчанию: {OpenOcdTclRpc.DEFAULT_PORT}"
    )
    parser.add_argument(
        '--adapter-speed',
        dest='adapter_speed',
        default=adapter_default_speed,
        help=f"Скорость отладчика в кГц. По умолчанию: {adapter_default_speed}"
    )
    parser.add_argument(
        '--openocd-exec',
        dest='openocd_exec',
        default=openocd_exec_path,
        help=f"Путь к исполняемому файлу openocd. По умолчанию: {openocd_exec_path}"
    )
    parser.add_argument(
        '--openocd-scripts',
        dest='openocd_scripts',
        default=openocd_scripts_path,
        help=f"Путь к папке scripts. По умолчанию: {openocd_scripts_path}"
    )
    parser.add_argument(
        '--openocd-interface',
        dest='openocd_interface',
        default=openocd_interface_path,
        help='Путь к файлу конфигурации отладчика относительно папки scripts или абсолютный путь. '
        f"По умолчанию: {openocd_interface_path}"
    )
    parser.add_argument(
        '--openocd-target',
        dest='openocd_target',
        default=openocd_target_path,
        help='Путь к файлу конфигурации целевого контроллера относительно папки scripts. '
        f"По умолчанию: {openocd_target_path}"
    )
    parser.add_argument(
        '--open-console',
        dest='open_console',
        action='store_true',
        default=False,
        help='Открывать OpenOCD в отдельной консоли'
    )
    parser.add_argument(
        '--boot-mode',
        dest='boot_mode',
        type=BootMode,
        choices=list(BootMode),
        default=BootMode.UNDEFINED,
        help="Выбор типа памяти, который отображается на загрузочную область. "
        "Если тип не выбран, данные, находящиеся в загрузочной области в hex файле отбрасываются. "
        f"По умолчанию: {BootMode.UNDEFINED}"
    )
    parser.add_argument(
        '--log-path',
        dest='log_path',
        default=default_log_path,
        help=f"Путь к файлу журнала. По умолчанию: {default_log_path}"
    )
    parser.add_argument(
        '--post-action',
        dest='post_action',
        default=default_post_action,
        help=f"Команды OpenOCD, запускаемые после прошивки. По умолчанию: {default_post_action}"
    )
    parser.add_argument(
        '--mcu-type',
        dest='mcu_type',
        type=MIK32_Version,
        choices=list(MIK32_Version),
        default=MIK32_Version.MIK32V2,
        help="Выбор микроконтроллера. "
        f"По умолчанию: {MIK32_Version.MIK32V2}"
    )
    parser.add_argument(
        '--no-driver',
        dest='use_driver',
        action='store_false',
        default=True,
        help='Отключает прошивку с использованием драйвера в ОЗУ'
    )
    return parser


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    parser = createParser()
    namespace = parser.parse_args()

    print(program_name)

    if namespace.filepath:
        exit(
            upload_file(
                namespace.filepath,
                host=namespace.openocd_host,
                port=namespace.openocd_port,
                is_run_openocd=namespace.run_openocd,
                use_quad_spi=namespace.use_quad_spi,
                openocd_exec=namespace.openocd_exec,
                openocd_scripts=namespace.openocd_scripts,
                openocd_interface=namespace.openocd_interface,
                openocd_target=namespace.openocd_target,
                adapter_speed=namespace.adapter_speed,
                is_open_console=namespace.open_console,
                boot_mode=namespace.boot_mode,
                log_path=namespace.log_path,
                post_action=namespace.post_action,
                mik_version=namespace.mcu_type,
                use_driver=namespace.use_driver,
            )
        )
    else:
        print("Nothing to upload")
