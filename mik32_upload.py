import shlex
import argparse
import socket
import subprocess
import os
import time
from enum import Enum
from typing import List, Dict, NamedTuple, Union
from hex_parser import FirmwareFile, MemorySection, MemoryType, Segment
from tclrpc import OpenOcdTclRpc, TclException
from mik32_gpio import MIK32_Version, gpio_init, gpio_deinit
from _version import applicaton_version
import mik32_eeprom
import mik32_spifi
import mik32_ram
import mik32_pm
from parsers import *
import logging
import sys

program_name = f'mik32-uploader-{applicaton_version}'

# class bcolors(Enum):
#     OK = '\033[92m'
#     WARNING = '\033[93m'
#     FAIL = '\033[91m'
#     ENDC = '\033[0m'
#     BOLD = '\033[1m'
#     UNDERLINE = '\033[4m'

if os.name == 'nt':
    openocd_exec = "openocd.exe"
else:
    openocd_exec = "openocd"

default_openocd_host = '127.0.0.1'
openocd_exec_path = os.path.join("openocd", "bin", openocd_exec)
openocd_scripts_path = os.path.join("openocd-scripts")
openocd_interface_path = os.path.join("interface", "ftdi", "mikron-link.cfg")
openocd_target_path = os.path.join("target", "mik32.cfg")
if os.name == 'nt':
    default_log_path = "nul"
else:
    default_log_path = "/dev/null"
default_post_action = "reset run"

adapter_default_speed = 500


def test_connection():
    output = ""
    with OpenOcdTclRpc() as openocd:
        try:
            output = openocd.run("capture \"reg\"")
        except OSError:
            logging.debug("Test connection timed out, try again")
            output = openocd.run("capture \"reg\"")

    if output == "":
        raise Exception("ERROR: no regs found, check MCU connection")


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


class OpenOCDStartupException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return f"OpenOCD Startup Exception: {self.msg}"


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
        mik_version=MIK32_Version.MIK32V2
) -> int:
    """
    Write ihex or binary file into MIK32 EEPROM or external flash memory
    @filename: full path to the file with hex or bin file format
    @return: return 0 if successful, 1 if failed
    """

    print(f"Using {mik_version.value}")

    result = 0

    if not os.path.exists(filename):
        print(f"ERROR: File {filename} does not exist")
        exit(1)

    file = FirmwareFile(filename, mik32_sections)

    segments: List[Segment] = file.get_segments()
    pages: Pages = form_pages(segments, boot_mode)

    proc: Union[subprocess.Popen, None] = None
    if is_run_openocd:
        try:
            logging.debug("OpenOCD try start!")

            proc = run_openocd(openocd_exec, openocd_scripts,
                               openocd_interface, openocd_target, is_open_console)

            logging.debug("OpenOCD started!")

        except OSError as e:
            raise OpenOCDStartupException(e)
    try:
        time.sleep(0.1)
        with OpenOcdTclRpc(host, port) as openocd:
            if (all(openocd_interface.find(i) == -1 for i in adapter_speed_not_supported)):
                openocd.run(f"adapter speed {adapter_speed}")
            openocd.run(f"log_output \"{log_path}\"")
            openocd.run(f"debug_level 1")

            logging.debug("OpenOCD configured!")

            mik32_pm.pm_init(openocd)

            logging.debug("PM configured!")

            if (pages.pages_eeprom.__len__() > 0):
                start_time = time.perf_counter()

                result |= mik32_eeprom.write_pages(
                    pages.pages_eeprom, openocd)

                write_time = time.perf_counter() - start_time
                write_size = pages.pages_eeprom.__len__(
                ) * memory_page_size[MemoryType.EEPROM]
                t = time.localtime()
                current_time = time.strftime("%H:%M:%S", t)
                print(
                    f"[{current_time}] Wrote {write_size} bytes in {write_time:.2f} seconds (effective {(write_size/(write_time*1024)):.1f} kbyte/s)")
            if (pages.pages_spifi.__len__() > 0):
                gpio_init(openocd, mik_version)
                start_time = time.perf_counter()

                result |= mik32_spifi.write_pages(
                    pages.pages_spifi, openocd, use_quad_spi=use_quad_spi)

                write_time = time.perf_counter() - start_time
                write_size = pages.pages_spifi.__len__(
                ) * memory_page_size[MemoryType.SPIFI]
                t = time.localtime()
                current_time = time.strftime("%H:%M:%S", t)
                print(
                    f"[{current_time}] Wrote {write_size} bytes in {write_time:.2f} seconds (effective {(write_size/(write_time*1024)):.1f} kbyte/s)")
                gpio_deinit(openocd, mik_version)

            segments_ram = list(filter(
                lambda segment: (segment.memory is not None) and (segment.memory.type == MemoryType.RAM), segments))
            if (segments_ram.__len__() > 0):
                mik32_ram.write_segments(segments_ram, openocd)
                result |= 0

            openocd.run(post_action)
    except ConnectionRefusedError:
        print("ERROR: The connection to OpenOCD is not established. Check the settings and connection of the debugger")
    except TclException as e:
        print(f"ERROR: TclException {e.code} \n {e.msg}")
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
    # parser.add_argument(
    #     '--log-terminal',
    #     dest='log_termir',
    #     action='store_true',
    #     default=False,
    #     help='Вывод журнала в консоль'
    # )
    parser.add_argument(
        '--post-action',
        dest='post_action',
        default=default_post_action,
        help=f"Команды OpenOCD, запускаемые после прошивки. По умолчанию: {default_post_action}"
    )
    parser.add_argument(
        '--no-color',
        dest='no_color',
        action='store_true',
        default=False,
        help='Вывод без последовательностей управления терминалом. Временно не используется'
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
    return parser


if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)

    parser = createParser()
    namespace = parser.parse_args()

    print(program_name)

    if namespace.filepath:
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
            mik_version=namespace.mcu_type
        )
    else:
        print("Nothing to upload")
