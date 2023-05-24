from typing import List
from mik32_upload import Segment
from tclrpc import TclException
from tclrpc import OpenOcdTclRpc
from pathlib import Path

from utils import bytes2words

def write_file(filename, is_resume=True):

    with OpenOcdTclRpc() as openocd:
        openocd.reset_halt()
        print(openocd.run("load_image {%s} 0x0" % Path(filename)))
        if is_resume:
            openocd.resume(0)
    print("RAM write file maybe done")


def write_segments(segments: List[Segment], openocd: OpenOcdTclRpc, is_resume=True):
    openocd.reset_halt()
    for segment in segments:
        print("Writing segment %s with size %d..." % (hex(segment.offset), segment.data.__len__()))
        segment_words = bytes2words(segment.data)
        openocd.write_memory(segment.offset, 32, segment_words)
    if is_resume:
        openocd.resume(0)
