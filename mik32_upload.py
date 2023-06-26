import shlex
import argparse
import subprocess
import os
from enum import Enum
from typing import List, Dict, NamedTuple, Union
from tclrpc import OpenOcdTclRpc, TclException
import mik32_eeprom
import mik32_spifi
import mik32_ram
from mik32_parsers import *


# class bcolors(Enum):
#     OK = '\033[92m'
#     WARNING = '\033[93m'
#     FAIL = '\033[91m'
#     ENDC = '\033[0m'
#     BOLD = '\033[1m'
#     UNDERLINE = '\033[4m'


openocd_exec_path = os.path.join("openocd", "bin", "openocd.exe")
openocd_scripts_path = os.path.join("openocd", "share", "openocd", "scripts")
openocd_interface_path = os.path.join("interface", "ftdi", "m-link.cfg")
openocd_target_path = os.path.join("target", "mik32.cfg")
default_log_path = "nul"
default_post_action = "reset run"

adapter_default_speed = 500

supported_text_formats = [".hex"]


def test_connection():
    output = ""
    with OpenOcdTclRpc() as openocd:
        output = openocd.run("capture \"reg\"")

    if output == "":
        raise Exception("ERROR: no regs found, check MCU connection")


class MemoryType(Enum):
    BOOT = 0
    EEPROM = 1
    RAM = 2
    SPIFI = 80
    UNKNOWN = -1


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


class MemorySection(NamedTuple):
    type: MemoryType
    offset: int
    length: int  # Memory section length in bytes


mik32v0_sections: List[MemorySection] = [
    MemorySection(MemoryType.BOOT, 0x0, 16 * 1024),
    MemorySection(MemoryType.EEPROM, 0x01000000, 8 * 1024),
    MemorySection(MemoryType.RAM, 0x02000000, 16 * 1024),
    MemorySection(MemoryType.SPIFI, 0x80000000, 8 * 1024 * 1024),
]


class Segment:
    offset: int
    memory: Union[MemorySection, None] = None
    data: List[int]

    def __init__(self, offset: int, data: List[int]):
        self.offset = offset
        self.data = data

        self._locate_memory_section()

    def _locate_memory_section(self):
        for section in mik32v0_sections:
            if self._belongs_memory_section(section, self.offset):
                self.memory = section

        if self.memory is None:
            raise Exception(
                f"ERROR: segment with offset {self.offset:#0x} doesn't belong to any section")

        if (self.offset + self.data.__len__()) > (self.memory.offset + self.memory.length):
            raise Exception(
                f"ERROR: segment with offset {self.offset:#0x} "
                f"and length {self.data.__len__()} "
                f"overflows section {self.memory.type.name}"
            )

    def _belongs_memory_section(self, memory_section: MemorySection, offset: int) -> bool:
        if offset < memory_section.offset:
            return False
        if offset >= (memory_section.offset + memory_section.length):
            return False

        return True


class FirmwareFile:
    file_name: str
    file_extension: str
    file_content: Union[List[str], List[int]] = []

    def __init__(self, path: str):
        self.file_name, self.file_extension = os.path.splitext(path)

        if self.file_extension in supported_text_formats:
            with open(path) as f:
                self.file_content = f.readlines()
        elif self.file_extension == ".bin":
            with open(path, "rb") as f:
                self.file_content = list(f.read())
        else:
            raise Exception(f"Unsupported file format: {self.file_extension}")

    def _parse_text(self) -> List[Segment]:
        segments: List[Segment] = []

        lba: int = 0        # Linear Base Address
        expect_address = 0  # Address of the next byte

        for i, line in enumerate(self.file_content):
            record: Record = parse_line(line, i, self.file_extension)
            if record.type == RecordType.DATA:
                drlo: int = record.address  # Data Record Load Offset
                if (expect_address != lba+drlo) or (segments.__len__() == 0):
                    expect_address = lba+drlo
                    segments.append(Segment(
                        offset=expect_address, data=[]))

                for byte in record.data:
                    segments[-1].data.append(byte)
                    expect_address += 1
            elif record.type == RecordType.EXTADDR:
                lba = record.address
            elif record.type == RecordType.LINEARSTARTADDR:
                print(f"Start Linear Address: {record.address:#10x}", )
            elif record.type == RecordType.EOF:
                break

        return segments

    def get_segments(self) -> List[Segment]:
        if self.file_extension in supported_text_formats:
            return self._parse_text()
        elif self.file_extension == ".bin":
            return [Segment(offset=0, data=self.file_content)]


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
    cmd = shlex.split(
        f"{openocd_exec} -s {openocd_scripts} "
        f"-f {openocd_interface} -f {openocd_target}", posix=False
    )

    creation_flags = subprocess.SW_HIDE
    if is_open_console:
        creation_flags |= subprocess.CREATE_NEW_CONSOLE

    proc = subprocess.Popen(
        cmd, creationflags=creation_flags)

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
        128
    )
    pages_spifi = segments_to_pages(
        filter_segments(segments, MemoryType.SPIFI,
                        boot_mode.to_memory_type()),
        256
    )

    return Pages(pages_eeprom, pages_spifi)


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
        post_action=default_post_action
) -> int:
    """
    Write ihex or binary file into MIK32 EEPROM or external flash memory
    @filename: full path to the file with hex or bin file format
    @return: return 0 if successful, 1 if failed
    """

    result = 0

    if not os.path.exists(filename):
        print(f"ERROR: File {filename} does not exist")
        exit(1)

    file = FirmwareFile(filename)

    segments: List[Segment] = file.get_segments()
    pages: Pages = form_pages(segments, boot_mode)

    proc: Union[subprocess.Popen, None] = None
    if is_run_openocd:
        try:
            proc = run_openocd(openocd_exec, openocd_scripts,
                            openocd_interface, openocd_target, is_open_console)
        except OSError as e:
            raise OpenOCDStartupException(e)
    try:
        with OpenOcdTclRpc(host, port) as openocd:
            openocd.run(f"adapter speed {adapter_speed}")
            openocd.run(f"log_output \"{log_path}\"")
            openocd.run(f"debug_level 1")

            if (pages.pages_eeprom.__len__() > 0):
                result |= mik32_eeprom.write_pages(
                    pages.pages_eeprom, openocd)
            if (pages.pages_spifi.__len__() > 0):
                result |= mik32_spifi.write_pages(
                    pages.pages_spifi, openocd, use_quad_spi=use_quad_spi)

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
    parser = argparse.ArgumentParser()
    parser.add_argument('filepath', nargs='?')
    parser.add_argument('--run-openocd', dest='run_openocd',
                        action='store_true', default=False)
    parser.add_argument('--use-quad-spi', dest='use_quad_spi',
                        action='store_true', default=False)
    parser.add_argument(
        '--openocd-host', dest='openocd_host', default='127.0.0.1')
    parser.add_argument('--openocd-port', dest='openocd_port',
                        default=OpenOcdTclRpc.DEFAULT_PORT)
    parser.add_argument('--adapter-speed', dest='adapter_speed',
                        default=adapter_default_speed)
    parser.add_argument(
        '--openocd-exec', dest='openocd_exec', default=openocd_exec_path)
    parser.add_argument(
        '--openocd-scripts', dest='openocd_scripts', default=openocd_scripts_path)
    parser.add_argument(
        '--openocd-interface', dest='openocd_interface', default=openocd_interface_path)
    parser.add_argument(
        '--openocd-target', dest='openocd_target', default=openocd_target_path)
    parser.add_argument('--open-console', dest='open_console',
                        action='store_true', default=False)
    parser.add_argument('-b', '--boot-mode', dest='boot_mode', type=BootMode,
                        choices=list(BootMode), default=BootMode.UNDEFINED)
    parser.add_argument('--log-path', dest='log_path',
                        default=default_log_path)
    parser.add_argument('--post-action', dest='post_action',
                        default=default_post_action)
    parser.add_argument('--no-color', dest='no_color',
                        action='store_true', default=False)

    return parser


if __name__ == '__main__':
    parser = createParser()
    namespace = parser.parse_args()

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
        )
    else:
        print("Nothing to upload")
