from .tclrpc import TclException
from .tclrpc import OpenOcdTclRpc
from pathlib import Path

def write_file(filename, is_resume=True):

    with OpenOcdTclRpc() as openocd:
        openocd.reset_halt()
        print(openocd.run("load_image {%s} 0x0" % Path(filename)))
        if is_resume:
            openocd.resume(0)
    print("RAM write file maybe done")
