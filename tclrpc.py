import re
import socket
from logging import getLogger
import time
from typing import List
logger = getLogger(__name__)

class TclException(Exception):
    def __init__(self, code, msg):
        self.code = code
        self.msg = msg

    def __repr__(self):
        return '\nTclException(%d, %r)' % (self.code, self.msg)

class TclPortError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __repr__(self):
        return 'TclPortError %r' % (self.msg)

_RE_SIMPLE_TCL_WORD = re.compile(r"^[a-zA-Z_0-9:+./@=,'-]+$")
def tcl_quote_word(word):
    """Quotes one word for TCL"""
    global _RE_SIMPLE_TCL_WORD
    if _RE_SIMPLE_TCL_WORD.match(word):
        return word
    else:
        return '{' + word + '}'

def tcl_quote_cmd(arg):
    """Quote a TCL command

    Argument must be a string (assumed to be already quoted) or list
    """
    if type(arg) is str:
        return arg
    elif type(arg) is list or type(arg) is tuple:
        return ' '.join([tcl_quote_word(word) for word in arg])
    else:
        raise TypeError("Expected str or list or tuple, got %s: %r" % (type(arg), arg))

class OpenOcdTclRpc:
    DEFAULT_PORT = 6666
    SEPARATOR_VALUE = 0x1a
    SEPARATOR_BYTES = b'\x1a'
    BUFFER_SIZE = 10240

    __slots__ = (
        'host',
        'port',
        'sock',
    )

    def __init__(self, host='127.0.0.1', port=DEFAULT_PORT):
        self.host = host
        self.port = port
        self.sock = None

    def __enter__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.wait_for_port()
        except socket.timeout:
            logger.debug("Test connection timed out, try again")
            self.sock.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect((self.host, self.port))
        return self

    def __exit__(self, *args):
        self.sock.close()
        self.sock = None

    def sendrecv(self, cmd):
        """Send a command string and return reply"""
        logger.debug('send: %s', cmd)
        data = cmd.encode('utf-8') + self.SEPARATOR_BYTES
        self.sock.sendall(data)
        reply = self._recv().decode('utf-8')
        logger.debug('recv: %s', reply)
        return reply

    def _recv(self):
        """Read bytes until self.SEPARATOR"""
        data = bytes()
        while True:
            chunk = self.sock.recv(self.BUFFER_SIZE)
            data += chunk
            index = data.find(self.SEPARATOR_BYTES)
            if index >= 0:
                if index != len(data) - 1:
                    raise TclPortError('Unhandled extra bytes after %r'.format(self.SEPARATOR_BYTES))
                return data[:-1]
        
    def wait_for_port(self, timeout: float = 5.0):
        sock = None
        start_time = time.perf_counter()
        while time.perf_counter() - start_time < timeout:
            try:
                sock = self.sock.connect((self.host, self.port))
                break
            except OSError as ex:
                time.sleep(0.01)
        if sock != None:
            self.sock = sock

    def run(self, cmd):
        """Run a command and raise an error if it returns an error"""
        wrap = 'set _code [catch {%s} _msg];expr {"$_code $_msg"}' % tcl_quote_cmd(cmd)
        reply = self.sendrecv(wrap)
        code, msg = reply.split(' ', 1)
        code = int(code)

        if code:
            raise TclException(code, msg)
        else:
            return msg
        
    def reset_halt(self):
        """Halt MCU and raise an error if it returns an error"""
        return self.run("capture \"reset halt\"")
    
    def halt(self):
        """Halt MCU and raise an error if it returns an error"""
        return self.run("capture \"halt\"")
    
    def resume(self, address=None):
        """Resume the target at its current code position, or the optional address 
        if it is provided. 
        OpenOCD will wait 5 seconds for the target to resume."""
        if address is None:
            return self.run(f"capture \"resume\"")
        else:
            return self.run(f"capture \"resume {address:#0x}\"")
    
    def mww(self, addr:int, word:int):
        """Write the word on addr and raise an error if it returns an error"""
        return self.run(f"capture \"mww {addr:#0x} {word:#0x}\"")
    
    def write_memory(self, address:int, width:int, data:List[int]):
        """This function provides an efficient way to write to the target memory 
        from a Tcl script
        
        address ... target memory address
        
        width ... memory access bit size, can be 8, 16, 32 or 64
        
        data ... Tcl list with the elements to write """
        data_words: List[str] = []
        for word in data:
            data_words.append(str(f"{word:#0x}"))
        data_string = " ".join(data_words)
        return self.run(f"capture \"write_memory {address:#0x} {width} {{{data_string}}}\"")
    
    def write_word(self, address:int, word:int):
        return self.write_memory(address, 32, [word])

    def read_memory(self, address:int, width:int, count:int):
        """This function provides an efficient way to read the target memory from a Tcl script. 
        A Tcl list containing the requested memory elements is returned by this function.

        address ... target memory address
        
        width ... memory access bit size, can be 8, 16, 32 or 64
        
        count ... number of elements to read """
        data = self.run(f"capture \"read_memory {address:#0x} {width} {count}\"").split(" ")
        return list(map(lambda word: int(word, base=16), data))
    
    def read_word(self, address:int):
        """This function provides an efficient way to read the target memory from a Tcl script. 
        A Tcl list containing the requested memory elements is returned by this function.

        address ... target memory address
        
        width ... memory access bit size, can be 8, 16, 32 or 64
        
        count ... number of elements to read """
        data = self.run(f"capture \"read_memory {address:#0x} 32 1\"").split(" ")
        return int(data[0], base=16)


