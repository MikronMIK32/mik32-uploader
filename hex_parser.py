from enum import Enum
import os
from typing import List, NamedTuple, Union

from parsers import ParserError, Record, RecordType, parse_line


class MemoryType(Enum):
    BOOT = 0
    EEPROM = 1
    RAM = 2
    SPIFI = 3
    UNKNOWN = -1


class MemorySection(NamedTuple):
    type: MemoryType
    offset: int
    length: int  # Memory section length in bytes


class Segment:
    offset: int
    memory: Union[MemorySection, None] = None
    data: List[int]

    def __init__(self, offset: int, data: List[int], sections: List[MemorySection]):
        self.offset = offset
        self.data = data

        self._locate_memory_section(sections)

    def _locate_memory_section(self, sections: List[MemorySection]):
        for section in sections:
            if self._belongs_memory_section(section, self.offset):
                self.memory = section

        if self.memory is None:
            raise ParserError(
                f"segment with offset {self.offset:#0x} doesn't belong to any section")

        if (self.offset + self.data.__len__()) > (self.memory.offset + self.memory.length):
            raise ParserError(
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


supported_text_formats = [".hex"]


class FirmwareFile:
    file_name: str
    file_extension: str
    segments: List[Segment] = []

    def __init__(self, path: str, sections: List[MemorySection]):
        self.file_name, self.file_extension = os.path.splitext(path)

        if self.file_extension in supported_text_formats:
            with open(path) as f:
                lines = f.readlines()
                self._parse_hex(lines, sections)
        elif self.file_extension == ".bin":
            with open(path, "rb") as f:
                bin_content = list(f.read())
                self.segments.append(Segment(offset=0, data=bin_content, sections=sections))
        else:
            raise ParserError(f"Unsupported file format: {self.file_extension}")

    def _parse_hex(self, lines: List[str], sections: List[MemorySection]): 
        segments: List[Segment] = []

        lba: int = 0        # Linear Base Address
        expect_address = 0  # Address of the next byte

        for i, line in enumerate(lines):
            record: Record = parse_line(line, i, self.file_extension)
            if record.type == RecordType.DATA:
                drlo: int = record.address  # Data Record Load Offset
                if (expect_address != lba+drlo) or (segments.__len__() == 0):
                    expect_address = lba+drlo
                    segments.append(Segment(
                        offset=expect_address, data=[], sections=sections))

                for byte in record.data:
                    segments[-1].data.append(byte)
                    expect_address += 1
            elif record.type == RecordType.EXTADDR:
                lba = record.address
            elif record.type == RecordType.EOF:
                break

        self.segments.extend(segments)

    def get_segments(self) -> List[Segment]:
        return self.segments
