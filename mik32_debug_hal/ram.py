from typing import List
from mik32_upload import Segment
from tclrpc import TclException
from tclrpc import OpenOcdTclRpc
from pathlib import Path
import time

from utils import bytes2words

def write_file(filename):

    with OpenOcdTclRpc() as openocd:
        openocd.halt()
        print(openocd.run("load_image {%s} 0x0" % Path(filename)))
    print("RAM write file maybe done")


def write_segments(segments: List[Segment], openocd: OpenOcdTclRpc):
    openocd.halt()
    for segment in segments:
        t = time.localtime()
        current_time = time.strftime("%H:%M:%S", t)
        print(f"[{current_time}] Writing segment %s with size %d..." % (hex(segment.offset), segment.data.__len__()))
        segment_words = bytes2words(segment.data)
        openocd.write_memory(segment.offset, 32, segment_words)


def check_segments(segments: List[Segment], openocd: OpenOcdTclRpc) -> int:
    openocd.halt()
    for segment in segments:
        print("Checking segment %s with size %d..." % (hex(segment.offset), segment.data.__len__()))
        segment_words = bytes2words(segment.data)
        segment_memory_words = openocd.read_memory(segment.offset, 32, len(segment_words))
        
        for i in range(len(segment_words)):
            if segment_words[i] != segment_memory_words[i]:
                print(f"Word [{i}] expect {segment_words[i]} != read {segment_memory_words[i]} in segment {segment.offset}")
                return 1
    
    return 0
