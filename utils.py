from typing import List


def bytes2words(arr: List[int]) -> List[int]:
    bytes = []
    words = []
    for byte in arr:
        bytes.append(byte)
        if bytes.__len__() == 4:
            words.append(bytes[0]+2**8*bytes[1]+2**16*bytes[2]+2**24*bytes[3])
            bytes = []
    if bytes.__len__() != 0:
        print("WARNING: skipping not-word-aligned byte")
    return words