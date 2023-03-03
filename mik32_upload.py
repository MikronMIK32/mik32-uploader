import shlex
from tclrpc import OpenOcdTclRpc
import argparse
import sys
import subprocess
import mik32_eeprom
import mik32_spifi
from typing import Iterable


# class bcolors:
#     OK = '\033[92m'
#     WARNING = '\033[93m'
#     FAIL = '\033[91m'
#     ENDC = '\033[0m'
#     BOLD = '\033[1m'
#     UNDERLINE = '\033[4m'


def parse_hex(file: str) -> dict:
    """
    TODO: Implement support for more record types
    """
    with open(file,
              "r", encoding='utf-8') as f:
        lines = f.readlines()

    memory_blocks = {}
    bytes = []
    block_offset = -1

    def add_memory_block():
        memory_blocks[block_offset] = bytes[:]

    is_error = False
    byte_len = 0

    next_line_offset = -1

    for i in range(lines.__len__()):
        line = lines[i]
        if line[0] != ':':
            print("Error: unexpected record mark on line %i, expect \':\', get \'%c\'" % (
                i+1, line[0]))
            is_error = True
            break

        reclen = int(line[1:3], base=16)        # Record length
        load_offset = int(line[3:7], base=16)   # Initial address of data byte
        rectype = int(line[7:9], base=16)       # Record type
        data_bytes: list[str] = []

        data_bytes_line = line[9:reclen*2 + 9]
        for i in range(reclen):
            data_bytes.append(data_bytes_line[i*2:i*2+2])
            byte_len += 1

        match rectype:
            case 0:  # Data Record
                if next_line_offset == -1:
                    next_line_offset = load_offset
                    block_offset = load_offset

                if next_line_offset != load_offset:
                    add_memory_block()
                    bytes.clear()
                    block_offset = load_offset
                    next_line_offset = load_offset

                for i in range(reclen):
                    byte = data_bytes[i]
                    byte = int(f"0x{byte}", base=16)
                    bytes.append(byte)

                next_line_offset += reclen

                # for i in range(data_len//4):
                #     data_bytes = word_bytes.reverse()
                # print("data words: ", data_words)
            case 1:  # End of File Record
                # print("End of File")
                add_memory_block()
            case 2:  # Extended Segment Address Record
                print("Record 2: Extended Segment Address Record")
                print("ERROR: unimplemented record type 2 on line %i" % (i+1))
                is_error = True
                break
            case 3:  # Start Segment Address Record
                print("Start Segment Address Record")
                print("ERROR: unimplemented record type 3 on line %i" % (i+1))
                is_error = True
            case 4:  # Extended Linear Address Record
                print("Extended Linear Address Record")
                print("ERROR: unimplemented record type 4 on line %i" % (i+1))
                is_error = True
            case 5:  # Start Linear Address Record
                print("Start Linear Address is 0x%s (line %i)" %
                      (data_bytes_line, (i+1)))
                print("MIK32 MCU does not support arbitrary start address")
            case _:
                print("ERROR: unexpected record type %i on line %i" %
                      (rectype, i+1))
                is_error = True
                break
        # print("line %i data_bytes=%i line_addr=%i" % (i+1, data_bytes, line_addr))

    # for word in memory_blocks[0]:
    #     print(f"{word:#0x}")

    if is_error:
        print("ERROR: error while parsing")
        exit()

    return memory_blocks


def parse_bin(filename: str) -> list[int]:
    arr: list[int] = []
    with open(filename, "rb") as f:
        while byte := f.read(1):
            arr.append(byte[0])
    return arr


def bytes2words(arr: list[int]) -> list[int]:
    word = []
    words = []
    for byte in arr:
        word.append(byte)
        if word.__len__() == 4:
            words.append(word[0]+2**8*word[1]+2**16*word[2]+2**24*word[3])
            word = []
    return words


def upload_file(filename: str, boot_source: str = "eeprom"):
    """
    Write ihex or binary file into MIK32 EEPROM or external flash memory

    @filename: full path to the file with hex or bin file format
    @boot_source: boot source, eeprom or spifi, define memory block mapped to boot memory area (0x0 offset)

    TODO: Implement error handling
    """
    if filename.endswith(".bin"):
        content = parse_bin(filename)
    elif filename.endswith(".hex"):
        content = parse_hex(filename)
    else:
        raise Exception("Unsupported file format")

    if boot_source == "eeprom":
        if type(content) is list:
            mik32_eeprom.write_words(bytes2words(content))
        elif type(content) is dict:
            mik32_eeprom.write_words(bytes2words(content[0]))
    elif boot_source == "spifi":
        if type(content) is list:
            mik32_spifi.spifi_write_file(content)
        elif type(content) is dict:
            mik32_spifi.spifi_write_file(content[0])
    else:
        raise Exception("Unsupported boot source, use eeprom or spifi")


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


# cmd = shlex.split("C://Users//shche//Desktop//MK32_Burner//openocd//bin//openocd.exe -s C://Users//shche//Desktop//MK32_Burner//openocd//share//openocd//scripts -f interface/ftdi/m-link.cfg -f target/mcu32.cfg")
# subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL)
# upload_file("C://Users//shche//Documents//PlatformIO//Projects//irq_test_compare//.pio//build//mik32-bluepill-v0//firmware.hex", "spifi")
# show_file("C://Users//shche//Documents//PlatformIO//Projects//irq_test_compare//.pio//build//mik32-bluepill-v0//firmware.hex", "spifi")
