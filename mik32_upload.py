import shlex
import argparse
import subprocess
import os
from enum import Enum
from typing import List, Dict, NamedTuple
from tclrpc import OpenOcdTclRpc
import mik32_eeprom
import mik32_spifi
import mik32_ram
from mik32_parsers import *
import config


# class bcolors(Enum):
#     OK = '\033[92m'
#     WARNING = '\033[93m'
#     FAIL = '\033[91m'
#     ENDC = '\033[0m'
#     BOLD = '\033[1m'
#     UNDERLINE = '\033[4m'


DEFAULT_OPENOCD_EXEC_FILE_PATH = os.path.join("openocd", "bin", "openocd.exe")
DEFAULT_OPENOCD_SCRIPTS_PATH = os.path.join(
    "openocd", "share", "openocd", "scripts")

supported_formats = [".hex"]

is_verbose = False

def test_connection():
    output = ""
    with OpenOcdTclRpc() as openocd:
        output = openocd.run(f"capture \"reg\"")

    if output == "":
        raise Exception("ERROR: no regs found, check MCU connection")


class MemoryType(Enum):
    BOOT = 0
    EEPROM = 1
    RAM = 2
    SPIFI = 80
    UNKNOWN = -1


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


@dataclass
class Segment:
    offset: int
    memory: MemorySection or None
    data: List[int]


def belongs_memory_section(memory_section: MemorySection, offset: int) -> bool:
    if offset < memory_section.offset:
        return False
    if offset >= (memory_section.offset + memory_section.length):
        return False

    return True


def find_memory_section(offset: int) -> MemorySection or None:
    for section in mik32v0_sections:
        if belongs_memory_section(section, offset):
            return section

    return None


def read_file(filename: str) -> List[Segment]:
    segments: List[Segment] = []
    lines: List[str] = []

    file_name, file_extension = os.path.splitext(filename)
    if file_extension in supported_formats:
        with open(filename) as f:
            lines = f.readlines()
    elif file_extension == ".bin":
        with open(filename, "rb") as f:
            contents = list(f.read())
            segments.append(
                Segment(offset=0, memory=find_memory_section(0), data=contents))
    else:
        raise Exception("Unsupported file format: %s" % (file_extension))

    lba: int = 0        # Linear Base Address
    expect_address = 0  # Address of the next byte

    for i, line in enumerate(lines):
        record: Record = parse_line(line, i, file_extension)
        if record.type == RecordType.DATA:
            drlo: int = record.address  # Data Record Load Offset
            if (expect_address != lba+drlo) or (segments.__len__() == 0):
                expect_address = lba+drlo
                segments.append(Segment(
                    offset=expect_address, memory=find_memory_section(expect_address), data=[]))

            for byte in record.data:
                segments[-1].data.append(byte)
                expect_address += 1
        elif record.type == RecordType.EXTADDR:
            lba = record.address
        elif record.type == RecordType.LINEARSTARTADDR:
            print("Start Linear Address:", record.address)
        elif record.type == RecordType.EOF:
            break

    return segments


def segment_to_pages(segment: Segment, page_size: int, pages: Dict[int, List[int]]):
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
        segment_to_pages(segment, page_size, pages)

    return pages


def upload_file(
    filename: str,
    openocd_path: str,
    scripts_path: str,
    adapter_speed: str,
    host: str = '127.0.0.1',
    port: int = OpenOcdTclRpc.DEFAULT_PORT,
    is_resume=True,
    run_openocd=False,
    use_quad_spi=False
) -> int:
    """
    Write ihex or binary file into MIK32 EEPROM or external flash memory

    @filename: full path to the file with hex or bin file format

    @return: return 0 if successful, 1 if failed
    """

    # print("Running OpenOCD...")

    # print(DEFAULT_OPENOCD_EXEC_FILE_PATH)
    # print(DEFAULT_OPENOCD_SCRIPTS_PATH)

    result = 0

    print(filename)
    if not os.path.exists(filename):
        print("ERROR: File %s does not exist" % filename)
        exit(1)

    segments: List[Segment] = read_file(filename)
    # print(segments)

    for segment in segments:
        if segment.memory is None:
            raise Exception(
                "ERROR: segment with offset %s doesn't belong to any section" % hex(segment.offset))

        if (segment.offset + segment.data.__len__()) > (segment.memory.offset + segment.memory.length):
            raise Exception("ERROR: segment with offset %s and length %s overflows section %s" % (
                hex(segment.offset), segment.data.__len__(), segment.memory.type.name))

    proc: subprocess.Popen or None = None
    if run_openocd:
        cmd = shlex.split("%s -s %s -f interface/ftdi/m-link.cfg -f target/mik32.cfg" % (
            openocd_path, scripts_path), posix=False)
        print(cmd)
        proc = subprocess.Popen(
            cmd, creationflags=subprocess.CREATE_NEW_CONSOLE | subprocess.SW_HIDE)

    with OpenOcdTclRpc() as openocd:
        pages_eeprom = segments_to_pages(list(filter(
            lambda segment: (segment.memory is not None) and (segment.memory.type == MemoryType.EEPROM), segments)), 128)
        pages_spifi = segments_to_pages(list(filter(
            lambda segment: (segment.memory is not None) and (segment.memory.type == MemoryType.SPIFI), segments)), 256)
        segments_ram = list(filter(
            lambda segment: (segment.memory is not None) and (segment.memory.type == MemoryType.RAM), segments))

        if (pages_eeprom.__len__() > 0):
            result |= mik32_eeprom.write_pages(
                pages_eeprom, openocd, is_resume)
        if (pages_spifi.__len__() > 0):
            # print(pages_spifi)
            result |= mik32_spifi.write_pages(
                pages_spifi, openocd, is_resume, use_quad_spi)
        if (segments_ram.__len__() > 0):
            mik32_ram.write_segments(segments_ram, openocd, is_resume)
            result |= 0

    if run_openocd and proc is not None:
        proc.kill()

    return result


def createParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('filepath', nargs='?')
    parser.add_argument('--openocd-path', dest='openocd_path',
                        default=DEFAULT_OPENOCD_EXEC_FILE_PATH)
    parser.add_argument('--scripts-path', dest='scripts_path',
                        default=DEFAULT_OPENOCD_SCRIPTS_PATH)
    parser.add_argument('--adapter-speed', dest='adapter_speed',
                        default=500)
    parser.add_argument('--run-openocd', dest='run_openocd',
                        action='store_true', default=False)
    parser.add_argument('--use-quad-spi', dest='use_quad_spi',
                        action='store_true', default=False)
    parser.add_argument(
        '--openocd-host', dest='openocd_host', default='127.0.0.1')
    parser.add_argument('--openocd-port', dest='openocd_port',
                        default=OpenOcdTclRpc.DEFAULT_PORT)
    parser.add_argument('--keep-halt', dest='keep_halt',
                        action='store_true', default=False)
    parser.add_argument('-v', '--verbose', dest='is_verbose',
                        action='store_true', default=False)
    # parser.add_argument('-b', '--boot-mode', default='undefined')

    return parser


if __name__ == '__main__':
    parser = createParser()
    namespace = parser.parse_args()
    config.is_verbose = namespace.is_verbose

    if namespace.filepath:
        upload_file(
            namespace.filepath,
            namespace.openocd_path,
            namespace.scripts_path,
            namespace.adapter_speed,
            host=namespace.openocd_host,
            port=namespace.openocd_port,
            is_resume=(not namespace.keep_halt),
            run_openocd=namespace.run_openocd,
            use_quad_spi=namespace.use_quad_spi,
        )
    else:
        print("Nothing to upload")
