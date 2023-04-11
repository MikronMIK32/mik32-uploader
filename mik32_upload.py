import shlex
from tclrpc import OpenOcdTclRpc
import argparse
import sys
import subprocess
import mik32_eeprom
import mik32_spifi
import mik32_ram
from mik32_parsers import *
import os
from typing import Iterable


# class bcolors:
#     OK = '\033[92m'
#     WARNING = '\033[93m'
#     FAIL = '\033[91m'
#     ENDC = '\033[0m'
#     BOLD = '\033[1m'
#     UNDERLINE = '\033[4m'

DEFAULT_OPENOCD_EXEC_FILE_PATH = os.path.join("openocd", "bin", "openocd.exe")
DEFAULT_OPENOCD_SCRIPTS_PATH = os.path.join("openocd", "share", "openocd", "scripts")


def test_connection():
    output = ""
    with OpenOcdTclRpc() as openocd:
        output = openocd.run(f"capture \"reg\"")
    
    if output == "":
        raise Exception("ERROR: no regs found, check MCU connection")


def upload_file(filename: str, boot_source: str = "eeprom") -> int:
    """
    Write ihex or binary file into MIK32 EEPROM or external flash memory

    @filename: full path to the file with hex or bin file format
    @boot_source: boot source, eeprom, ram or spifi, define memory block mapped to boot memory area (0x0 offset)

    TODO: Implement error handling
    """

    print("Boot mode %s" % boot_source)

    print("Running OpenOCD...")

    print(DEFAULT_OPENOCD_EXEC_FILE_PATH)
    print(DEFAULT_OPENOCD_SCRIPTS_PATH)

    if not os.path.exists(filename):
        print("ERROR: File %s does not exist" % filename)
        exit(1)

    cmd = shlex.split("%s -s %s -f interface/ftdi/m-link.cfg -f target/mcu32.cfg" % (DEFAULT_OPENOCD_EXEC_FILE_PATH, DEFAULT_OPENOCD_SCRIPTS_PATH), posix=False)
    with subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL) as proc:
        if boot_source == "eeprom":
            result = mik32_eeprom.write_words(bytes2words(get_content(filename)))
        elif boot_source == "spifi":
            mik32_spifi.spifi_write_file(get_content(filename))
            result = 0 # TODO
        elif boot_source == "ram":
            mik32_ram.write_file(filename)
            result = 0 # TODO
        else:
            raise Exception("Unsupported boot source, use eeprom or spifi")
            result = 1
        proc.kill()
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
    parser.add_argument('-b', '--boot-mode', default='eeprom')

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
