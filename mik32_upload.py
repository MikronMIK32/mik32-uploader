import shlex
import argparse
import sys
import subprocess
import os
from enum import Enum
from typing import List, Tuple
from .drivers.tclrpc import OpenOcdTclRpc
from .drivers.mik32_eeprom import *
from .drivers.mik32_spifi import *
from .drivers.mik32_ram import *
from .mik32_parsers import *
from .parsers.parser_hex import *


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


def test_connection():
    output = ""
    with OpenOcdTclRpc() as openocd:
        output = openocd.run(f"capture \"reg\"")

    if output == "":
        raise Exception("ERROR: no regs found, check MCU connection")


def read_file(filename: str) -> List[Tuple[int, List[int]]] :
    segments: List[Tuple[int, List[int]]] = []
    lines: List[str] = []

    file_name, file_extension = os.path.splitext(filename)
    if file_extension in supported_formats:
        with open(filename) as f:
            lines = f.readlines()
    elif file_extension == ".bin":
        with open(filename, "rb") as f:
            contents = list(f.read())
            segments[0] = (0, contents)
    else:
        raise Exception("Unsupported file format: %s" % (file_extension))

    for line in lines:
        record: Tuple[RecordType, List[int]]
        if file_extension == ".hex":
            record = 

    
    return segments


def get_content(filename: str) -> List[int]:
    content: List[int] = []

    if filename.endswith(".bin"):
        content = parse_bin(filename)
    elif filename.endswith(".hex"):
        content = parse_hex(filename)[0]
    else:
        
    
    return content


def upload_file(filename: str, boot_source: str = "undefined", is_resume=True) -> int:
    """
    Write ihex or binary file into MIK32 EEPROM or external flash memory

    @filename: full path to the file with hex or bin file format
    @boot_source: boot source, eeprom, ram or spifi, define memory block mapped to boot memory area (0x0 offset)

    @return: return 0 if successful, 1 if failed

    TODO: Implement error handling
    """

    print("Boot mode %s" % boot_source)

    print("Running OpenOCD...")

    print(DEFAULT_OPENOCD_EXEC_FILE_PATH)
    print(DEFAULT_OPENOCD_SCRIPTS_PATH)

    if not os.path.exists(filename):
        print("ERROR: File %s does not exist" % filename)
        exit(1)

    # cmd = shlex.split("%s -s %s -f interface/ftdi/m-link.cfg -f target/mcu32.cfg" % (DEFAULT_OPENOCD_EXEC_FILE_PATH, DEFAULT_OPENOCD_SCRIPTS_PATH), posix=False)
    # with subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL) as proc:
    #     if boot_source == "eeprom":
    #         result = write_words(bytes2words(get_content(filename)))
    #     elif boot_source == "spifi":
    #         spifi_write_file(get_content(filename))
    #         result = 0 # TODO
    #     elif boot_source == "ram":
    #         write_file(filename)
    #         result = 0 # TODO
    #     else:
    #         raise Exception("Unsupported boot source, use eeprom or spifi")
    #         result = 1
    #     proc.kill()

    if boot_source == "eeprom":
        result = write_words(bytes2words(get_content(filename)), is_resume)
    elif boot_source == "spifi":
        result = spifi_write_file(get_content(filename), is_resume)
    elif boot_source == "ram":
        write_file(filename, is_resume)
        result = 0  # TODO
    else:
        raise Exception("Unsupported boot source, use eeprom or spifi")
        result = 1

    return result


def show_file(filename: str, boot_source: str = "eeprom"):
    if filename.endswith(".bin"):
        content = parse_bin(filename)
    elif filename.endswith(".hex"):
        content = parse_hex(filename)
    else:
        raise Exception("Unsupported file format")

    if type(content) is list:
        print(content)
    elif type(content) is dict:
        print(content[0])


def createParser():
    parser = argparse.ArgumentParser()
    parser.add_argument('filepath', nargs='?')
    parser.add_argument('--show-file', action="store_const", const=True)
    parser.add_argument('--no-upload', action="store_const", const=True)
    parser.add_argument('-b', '--boot-mode', default='undefined')

    return parser


if __name__ == '__main__':
    parser = createParser()
    namespace = parser.parse_args()

    if namespace.show_file:
        show_file(namespace.filepath)
    if namespace.filepath:
        if namespace.no_upload == None:
            upload_file(namespace.filepath, namespace.boot_mode)
    else:
        print("Nothing to upload")
