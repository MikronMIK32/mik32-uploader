from enum import Enum
from typing import Dict, List
import time
from tclrpc import TclException
from tclrpc import OpenOcdTclRpc


# --------------------------
# DMA register offset
# --------------------------
DMA_REGS_BASE_ADDRESS = 0x00040000

DMA_CONTROL = DMA_REGS_BASE_ADDRESS + 0x40

DMA_CHANNEL_SIZEOF = 0x4 * 4


def DMA_CHANNEL_DESTINATION(i):
    return DMA_REGS_BASE_ADDRESS + i*DMA_CHANNEL_SIZEOF + 0x4*0


def DMA_CHANNEL_SOURCE(i):
    return DMA_REGS_BASE_ADDRESS + i*DMA_CHANNEL_SIZEOF + 0x4*1


def DMA_CHANNEL_LEN(i):
    return DMA_REGS_BASE_ADDRESS + i*DMA_CHANNEL_SIZEOF + 0x4*2


def DMA_CHANNEL_CONFIG(i):
    return DMA_REGS_BASE_ADDRESS + i*DMA_CHANNEL_SIZEOF + 0x4*3

# --------------------------
# DMA register fields
# --------------------------


DMA_CHANNEL_COUNT = 4

DMA_CHANNEL_M = ((1 << DMA_CHANNEL_COUNT) - 1)

# DMA_CONTROL

DMA_CONTROL_CLEAR_LOCAL_IRQ_S = 0
DMA_CONTROL_CLEAR_LOCAL_IRQ_M = (
    DMA_CHANNEL_M << DMA_CONTROL_CLEAR_LOCAL_IRQ_S)


def DMA_CONTROL_CLEAR_LOCAL_IRQ(i):
    return ((1 << (DMA_CONTROL_CLEAR_LOCAL_IRQ_S + (i))) & DMA_CONTROL_CLEAR_LOCAL_IRQ_M)


DMA_CONTROL_CLEAR_GLOBAL_IRQ_S = (DMA_CHANNEL_COUNT + 0)
DMA_CONTROL_CLEAR_GLOBAL_IRQ_M = (1 << DMA_CONTROL_CLEAR_GLOBAL_IRQ_S)
DMA_CONTROL_CLEAR_ERROR_IRQ_S = (DMA_CHANNEL_COUNT + 1)
DMA_CONTROL_CLEAR_ERROR_IRQ_M = (1 << DMA_CONTROL_CLEAR_ERROR_IRQ_S)
DMA_CONTROL_GLOBAL_IRQ_ENA_S = (DMA_CHANNEL_COUNT + 2)
DMA_CONTROL_GLOBAL_IRQ_ENA_M = (1 << DMA_CONTROL_GLOBAL_IRQ_ENA_S)
DMA_CONTROL_ERROR_IRQ_ENA_S = (DMA_CHANNEL_COUNT + 3)
DMA_CONTROL_ERROR_IRQ_ENA_M = (1 << DMA_CONTROL_ERROR_IRQ_ENA_S)
DMA_CONTROL_CURRENT_VALUE_S = (DMA_CHANNEL_COUNT + 4)
DMA_CONTROL_CURRENT_VALUE_M = (1 << DMA_CONTROL_CURRENT_VALUE_S)

DMA_CFG_CH_ENABLE_S = 0
DMA_CFG_CH_ENABLE_M = (1 << DMA_CFG_CH_ENABLE_S)
DMA_CFG_CH_DISABLE_M = (0 << DMA_CFG_CH_ENABLE_S)

DMA_CFG_CH_PRIOR_S = 1
DMA_CFG_CH_PRIOR_M = (0x3 << DMA_CFG_CH_PRIOR_S)

DMA_CFG_CH_READ_MODE_S = 3
DMA_CFG_CH_READ_MODE_memory_M = (1 << DMA_CFG_CH_READ_MODE_S)
DMA_CFG_CH_READ_MODE_periphery_M = (0 << DMA_CFG_CH_READ_MODE_S)

DMA_CFG_CH_WRITE_MODE_S = 4
DMA_CFG_CH_WRITE_MODE_memory_M = (1 << DMA_CFG_CH_WRITE_MODE_S)
DMA_CFG_CH_WRITE_MODE_periphery_M = (0 << DMA_CFG_CH_WRITE_MODE_S)

DMA_CFG_CH_READ_INCREMENT_S = 5
DMA_CFG_CH_READ_INCREMENT_M = (1 << DMA_CFG_CH_READ_INCREMENT_S)
DMA_CFG_CH_READ_no_INCREMENT_M = (0 << DMA_CFG_CH_READ_INCREMENT_S)

DMA_CFG_CH_READ_INCREMENT_S = 5
DMA_CFG_CH_READ_INCREMENT_M = (1 << DMA_CFG_CH_READ_INCREMENT_S)
DMA_CFG_CH_READ_no_INCREMENT_M = (0 << DMA_CFG_CH_READ_INCREMENT_S)

DMA_CFG_CH_WRITE_INCREMENT_S = 6
DMA_CFG_CH_WRITE_INCREMENT_M = (1 << DMA_CFG_CH_WRITE_INCREMENT_S)
DMA_CFG_CH_WRITE_no_INCREMENT_M = (0 << DMA_CFG_CH_WRITE_INCREMENT_S)

DMA_CFG_CH_READ_SIZE_S = 7
DMA_CFG_CH_READ_SIZE_byte_M = (0B00 << DMA_CFG_CH_READ_SIZE_S)    # байт
DMA_CFG_CH_READ_SIZE_2byte_M = (0B01 << DMA_CFG_CH_READ_SIZE_S)    # полуслово
DMA_CFG_CH_READ_SIZE_4byte_M = (0B10 << DMA_CFG_CH_READ_SIZE_S)    # слово
DMA_CFG_CH_READ_SIZE_rez_M = (0B11 << DMA_CFG_CH_READ_SIZE_S)    # резерв

DMA_CFG_CH_WRITE_SIZE_S = 9
DMA_CFG_CH_WRITE_SIZE_byte_M = (0B00 << DMA_CFG_CH_WRITE_SIZE_S)   # байт
DMA_CFG_CH_WRITE_SIZE_2byte_M = (0B01 << DMA_CFG_CH_WRITE_SIZE_S)   # полуслово
DMA_CFG_CH_WRITE_SIZE_4byte_M = (0B10 << DMA_CFG_CH_WRITE_SIZE_S)   # слово
DMA_CFG_CH_WRITE_SIZE_rez_M = (0B11 << DMA_CFG_CH_WRITE_SIZE_S)   # резерв

# Кол-во байт пакетной передачи:   2^Read_burst_size
DMA_CFG_CH_READ_BURST_SIZE_S = 11
# Кол-во байт пакетной передачи:   2^Write_burst_size
DMA_CFG_CH_WRITE_BURST_SIZE_S = 14

DMA_CFG_CH_READ_REQ_S = 17    # выбор канала чтения
DMA_CFG_CH_READ_REQ_M = (0xF << DMA_CFG_CH_READ_REQ_S)


def DMA_CFG_CH_READ_REQ(v):
    return (((v) << DMA_CFG_CH_READ_REQ_S) & DMA_CFG_CH_READ_REQ_M)


DMA_CFG_CH_WRITE_REQ_S = 21    # выбор канала записи
DMA_CFG_CH_WRITE_REQ_M = (0xF << DMA_CFG_CH_WRITE_REQ_S)


def DMA_CFG_CH_WRITE_REQ(v):
    return (((v) << DMA_CFG_CH_WRITE_REQ_S) & DMA_CFG_CH_WRITE_REQ_M)


DMA_CFG_CH_ACK_READ_S  = 25
DMA_CFG_CH_ACK_READ_M  = (1 << DMA_CFG_CH_ACK_READ_S)
DMA_CFG_CH_ACK_WRITE_S = 26
DMA_CFG_CH_ACK_WRITE_M = (1 << DMA_CFG_CH_ACK_WRITE_S)

DMA_STATUS_READY_S     = 0


# ReadStatus. Разрешить читать текущий статус канала
class CurrentValue(Enum):
    ENABLE = 0  # Текущие значения
    DISABLE = 1  # Значения при настройке


class ChannelIndex(Enum):
    CHANNEL_0 = 0
    CHANNEL_1 = 1
    CHANNEL_2 = 2
    CHANNEL_3 = 3


class ChannelPriority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2
    VERY_HIGH = 3


class ChannelMode(Enum):
    PERIPHERY = 0
    MEMORY = 1


class ChannelIncrement(Enum):
    DISABLE = 0
    ENABLE = 1


class ChannelSize(Enum):
    BYTE = 0
    HALFWORD = 1
    WORD = 1


class ChannelAck(Enum):
    DISABLE = 0
    ENABLE = 1


class ChannelRequest(Enum):
    USART_0_REQUEST = 0
    USART_1_REQUEST = 1
    CRYPTO_REQUEST = 2
    SPI_0_REQUEST = 3
    SPI_1_REQUEST = 4
    I2C_0_REQUEST = 5
    I2C_1_REQUEST = 6
    SPIFI_REQUEST = 7
    TIMER32_1_REQUEST = 8
    TIMER32_2_REQUEST = 9
    TIMER32_0_REQUEST = 10


class DMA_Channel:
    openocd: OpenOcdTclRpc

    write_buffer: int = 0

    channel: ChannelIndex
    priority: ChannelPriority

    read_mode: ChannelMode
    read_increment: ChannelIncrement
    read_size: ChannelSize
    read_ack: ChannelAck
    read_burst_size: int
    read_request: ChannelRequest

    write_mode: ChannelMode
    write_increment: ChannelIncrement
    write_size: ChannelSize
    write_ack: ChannelAck
    write_burst_size: int
    write_request: ChannelRequest

    def __init__(self, openocd: OpenOcdTclRpc):
        self.openocd = openocd

    def set_source(self, source: int):
        self.openocd.write_word(DMA_CHANNEL_SOURCE(1), source)

    def set_destination(self, source: int):
        self.openocd.write_word(DMA_CHANNEL_DESTINATION(1), source)

    def set_length(self, source: int):
        self.openocd.write_word(DMA_CHANNEL_LEN(1), source)

    def set_config(self, source: int):
        self.openocd.write_word(DMA_CHANNEL_CONFIG(1), source)

    def start(
            self,
            source_address: int,
            destination_address: int,
            length: int,
    ):
        self.write_buffer |= (DMA_CFG_CH_ENABLE_M
                              | (self.priority.value << DMA_CFG_CH_PRIOR_S)
                              | (self.read_mode.value << DMA_CFG_CH_READ_MODE_S)
                              | (self.read_increment.value << DMA_CFG_CH_READ_INCREMENT_S)
                              | (self.read_size.value << DMA_CFG_CH_READ_SIZE_S)
                              | (self.read_burst_size << DMA_CFG_CH_READ_BURST_SIZE_S)
                              | (self.read_request.value << DMA_CFG_CH_READ_REQ_S)
                              | (self.read_ack.value << DMA_CFG_CH_ACK_READ_S)
                              | (self.write_mode.value << DMA_CFG_CH_WRITE_MODE_S)
                              | (self.write_increment.value << DMA_CFG_CH_WRITE_INCREMENT_S)
                              | (self.write_size.value << DMA_CFG_CH_WRITE_SIZE_S)
                              | (self.write_burst_size << DMA_CFG_CH_WRITE_BURST_SIZE_S)
                              | (self.write_request.value << DMA_CFG_CH_WRITE_REQ_S)
                              | (self.write_ack.value << DMA_CFG_CH_ACK_WRITE_S))

        self.openocd.write_memory(DMA_CHANNEL_DESTINATION(1), 32, [destination_address, source_address, length, self.write_buffer])


class DMA:
    openocd: OpenOcdTclRpc

    current_value: CurrentValue = CurrentValue.ENABLE
    write_buffer: int = 0

    channels: List[DMA_Channel] = []

    def __init__(self, openocd: OpenOcdTclRpc):
        self.openocd = openocd
        self.channels.append(DMA_Channel(self.openocd))
        self.channels.append(DMA_Channel(self.openocd))
        self.channels.append(DMA_Channel(self.openocd))
        self.channels.append(DMA_Channel(self.openocd))

    def init(self):
        self.current_value = CurrentValue.ENABLE

        self.write_buffer = 0
        self.openocd.write_memory(0x40000, 32, [0] * 16)
        self.clear_irq()
        self.set_current_value(self.current_value)

    def set_control(self, control: int):
        if (control > 2**32 or control < 0):
            raise ValueError

        self.openocd.write_word(DMA_CONTROL, control)

    def get_control(self) -> int:
        return self.openocd.read_word(DMA_CONTROL)

    def clear_irq(self):
        self.clear_local_irq()
        self.clear_global_irq()
        self.clear_error_irq()

    def clear_local_irq(self):
        self.write_buffer &= ~(DMA_CONTROL_CLEAR_LOCAL_IRQ_M |
                               DMA_CONTROL_CLEAR_GLOBAL_IRQ_M | DMA_CONTROL_CLEAR_ERROR_IRQ_M)
        self.write_buffer |= DMA_CONTROL_CLEAR_LOCAL_IRQ_M
        self.set_control(self.write_buffer)
        self.write_buffer &= ~(DMA_CONTROL_CLEAR_LOCAL_IRQ_M |
                               DMA_CONTROL_CLEAR_GLOBAL_IRQ_M | DMA_CONTROL_CLEAR_ERROR_IRQ_M)

    def clear_global_irq(self):
        self.write_buffer &= ~(DMA_CONTROL_CLEAR_LOCAL_IRQ_M |
                               DMA_CONTROL_CLEAR_GLOBAL_IRQ_M | DMA_CONTROL_CLEAR_ERROR_IRQ_M)
        self.write_buffer |= DMA_CONTROL_CLEAR_GLOBAL_IRQ_M
        self.set_control(self.write_buffer)
        self.write_buffer &= ~(DMA_CONTROL_CLEAR_LOCAL_IRQ_M |
                               DMA_CONTROL_CLEAR_GLOBAL_IRQ_M | DMA_CONTROL_CLEAR_ERROR_IRQ_M)

    def clear_error_irq(self):
        self.write_buffer &= ~(DMA_CONTROL_CLEAR_LOCAL_IRQ_M |
                               DMA_CONTROL_CLEAR_GLOBAL_IRQ_M | DMA_CONTROL_CLEAR_ERROR_IRQ_M)
        self.write_buffer |= DMA_CONTROL_CLEAR_ERROR_IRQ_M
        self.set_control(self.write_buffer)
        self.write_buffer &= ~(DMA_CONTROL_CLEAR_LOCAL_IRQ_M |
                               DMA_CONTROL_CLEAR_GLOBAL_IRQ_M | DMA_CONTROL_CLEAR_ERROR_IRQ_M)

    def set_current_value(self, current_value: CurrentValue):
        self.current_value = current_value
        self.write_buffer &= ~(DMA_CONTROL_CURRENT_VALUE_M)
        self.write_buffer |= current_value.value << DMA_CONTROL_CURRENT_VALUE_S
        self.set_control(self.write_buffer)
    
    def dma_wait(self, channel: DMA_Channel, timeout: float):
        channel_index = channel.channel.value
        mask = (1 << channel_index) << DMA_STATUS_READY_S

        begin = time.perf_counter()

        while (begin - time.perf_counter()) < timeout:
            if self.get_control() & mask != 0:
                return
        
        raise Exception

