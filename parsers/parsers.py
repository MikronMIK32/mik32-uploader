from enum import Enum
from typing import List, Tuple
import parser_hex


class RecordType(Enum):
    DATA = 1


def parse_line(line: str, file_extension: str) -> Tuple[RecordType, List[int]]:
    record: Tuple[RecordType, List[int]]

    if file_extension == ".hex":
        

    return record