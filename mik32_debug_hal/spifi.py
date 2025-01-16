from enum import Enum
from typing import List, Union
import time
from tclrpc import OpenOcdTclRpc
import mik32_debug_hal.registers.memory_map as mem_map
import mik32_debug_hal.registers.bitfields.spifi as spifi_fields
import mik32_debug_hal.dma as dma


class SPIFI():

    DEFAULT_READ_DATA_COMMAND = 0x03

    class SpifiError(Exception):
        def __init__(self, value):
            self.value = value

        def __str__(self):
            return ("ERROR: " + repr(self.value))

    class Frameform(Enum):
        RESERVED = 0
        OPCODE_NOADDR = 1
        OPCODE_1ADDR = 2
        OPCODE_2ADDR = 3
        OPCODE_3ADDR = 4
        OPCODE_4ADDR = 5
        NOOPCODE_3ADDR = 6
        NOOPCODE_4ADDR = 7

    class Fieldform(Enum):
        ALL_SERIAL = 0
        DATA_PARALLEL = 1
        OPCODE_SERIAL = 2
        ALL_PARALLEL = 3

    class Direction(Enum):
        READ = 0
        WRITE = 1

    INIT_DELAY = 0.001

    TIMEOUT = 1.0

    openocd: OpenOcdTclRpc

    def __init__(self, openocd: OpenOcdTclRpc):
        self.openocd = openocd

        self.init()

    def intrq_clear(self):
        self.openocd.write_word(mem_map.SPIFI_CONFIG_STAT, self.openocd.read_word(mem_map.SPIFI_CONFIG_STAT) |
                                spifi_fields.SPIFI_CONFIG_STAT_INTRQ_M)

    def init_periphery(self):
        self.openocd.write_word(mem_map.SPIFI_CONFIG_STAT, self.openocd.read_word(mem_map.SPIFI_CONFIG_STAT) |
                                #    SPIFI_CONFIG_STAT_INTRQ_M |
                                spifi_fields.SPIFI_CONFIG_STAT_RESET_M)
        # openocd.write_word(SPIFI_CONFIG_CTRL, openocd.read_word(
        #     SPIFI_CONFIG_CTRL) | (7 << SPIFI_CONFIG_CTRL_SCK_DIV_S))
        self.openocd.write_word(mem_map.SPIFI_CONFIG_ADDR, 0x00)
        self.openocd.write_word(mem_map.SPIFI_CONFIG_IDATA, 0x00)
        self.openocd.write_word(mem_map.SPIFI_CONFIG_CLIMIT, 0x00)

        time.sleep(self.INIT_DELAY)

    def init(self):

        self.init_periphery()

        control = self.openocd.read_word(mem_map.SPIFI_CONFIG_CTRL)
        control |= spifi_fields.SPIFI_CONFIG_CTRL_DMAEN_M
        self.openocd.write_word(mem_map.SPIFI_CONFIG_CTRL, control)

        time.sleep(self.INIT_DELAY)

    def init_memory(self):
        self.openocd.write_word(mem_map.SPIFI_CONFIG_STAT, self.openocd.read_word(mem_map.SPIFI_CONFIG_STAT) |
                                spifi_fields.SPIFI_CONFIG_STAT_INTRQ_M |
                                spifi_fields.SPIFI_CONFIG_STAT_RESET_M)
        # openocd.write_word(SPIFI_CONFIG_CTRL, openocd.read_word(
        #     SPIFI_CONFIG_CTRL) | (7 << SPIFI_CONFIG_CTRL_SCK_DIV_S))
        self.openocd.write_word(mem_map.SPIFI_CONFIG_ADDR, 0x00)
        self.openocd.write_word(mem_map.SPIFI_CONFIG_IDATA, 0x00)
        self.openocd.write_word(mem_map.SPIFI_CONFIG_CLIMIT, 0x00)
        self.openocd.write_word(mem_map.SPIFI_CONFIG_MCMD, (0 << spifi_fields.SPIFI_CONFIG_MCMD_INTLEN_S) |
                                (spifi_fields.SPIFI_CONFIG_CMD_FIELDFORM_ALL_SERIAL << spifi_fields.SPIFI_CONFIG_MCMD_FIELDFORM_S) |
                                (spifi_fields.SPIFI_CONFIG_CMD_FRAMEFORM_OPCODE_3ADDR << spifi_fields.SPIFI_CONFIG_MCMD_FRAMEFORM_S) |
                                (self.DEFAULT_READ_DATA_COMMAND << spifi_fields.SPIFI_CONFIG_MCMD_OPCODE_S))

        time.sleep(self.INIT_DELAY)

    def spifi_wait_intrq_timeout(self, error_message: str):
        time_end = time.perf_counter() + self.TIMEOUT
        while time.perf_counter() < time_end:
            if (self.openocd.read_word(mem_map.SPIFI_CONFIG_STAT) & spifi_fields.SPIFI_CONFIG_STAT_INTRQ_M) != 0:
                return
        raise self.SpifiError(error_message)

    def send_command(
            self,
            cmd: int,
            frameform: Frameform,
            fieldform: Fieldform,
            byte_count=0,
            address=0,
            idata=0,
            cache_limit=0,
            idata_length=0,
            direction=Direction.READ,
            data: List[int] = [],
            dma: Union[dma.DMA, None] = None
    ) -> List[int]:
        if (dma is not None) and (direction == self.Direction.WRITE):
            self.openocd.write_memory(0x02003F00, 8, data)

            dma.channels[0].start(
                0x02003F00,
                mem_map.SPIFI_CONFIG_DATA32,
                255
            )
        elif (dma is not None) and (direction == self.Direction.READ):
            dma.channels[1].start(
                mem_map.SPIFI_CONFIG_DATA32,
                0x02003F00,
                255
            )

        self.openocd.write_memory(
            mem_map.SPIFI_CONFIG_ADDR, 32, [address, idata])

        cmd_write_value = ((cmd << spifi_fields.SPIFI_CONFIG_CMD_OPCODE_S) |
                           (frameform.value << spifi_fields.SPIFI_CONFIG_CMD_FRAMEFORM_S) |
                           (fieldform.value << spifi_fields.SPIFI_CONFIG_CMD_FIELDFORM_S) |
                           (byte_count << spifi_fields.SPIFI_CONFIG_CMD_DATALEN_S) |
                           (idata_length << spifi_fields.SPIFI_CONFIG_CMD_INTLEN_S) |
                           (direction.value << spifi_fields.SPIFI_CONFIG_CMD_DOUT_S))

        self.openocd.write_memory(
            mem_map.SPIFI_CONFIG_CMD, 32, [cmd_write_value])

        if direction == self.Direction.READ:
            out_list = []
            if dma is not None:
                dma.dma_wait(dma.channels[1], 0.1)
                out_list.extend(self.openocd.read_memory(
                    0x02003F00, 8, byte_count))

                return out_list
            else:
                for i in range(byte_count):
                    out_list.append(self.openocd.read_memory(
                        mem_map.SPIFI_CONFIG_DATA32, 8, 1)[0])
                return out_list

        if direction == self.Direction.WRITE:
            if dma is not None:
                dma.dma_wait(dma.channels[0], 0.1)
            else:
                if (byte_count % 4) == 0:
                    for i in range(0, byte_count, 4):
                        self.openocd.write_memory(mem_map.SPIFI_CONFIG_DATA32, 32, [
                            data[i] + data[i+1] * 256 + data[i+2] * 256 * 256 + data[i+3] * 256 * 256 * 256])
                else:
                    for i in range(byte_count):
                        self.openocd.write_memory(
                            mem_map.SPIFI_CONFIG_DATA32, 8, [data[i]])

        return []

    def dma_config(self) -> dma.DMA:
        dma_instance = dma.DMA(self.openocd)
        dma_instance.init()

        dma_instance.channels[0].write_buffer = 0

        dma_instance.channels[0].channel = dma.ChannelIndex.CHANNEL_0
        dma_instance.channels[0].priority = dma.ChannelPriority.VERY_HIGH

        dma_instance.channels[0].read_mode = dma.ChannelMode.MEMORY
        dma_instance.channels[0].read_increment = dma.ChannelIncrement.ENABLE
        dma_instance.channels[0].read_size = dma.ChannelSize.WORD
        dma_instance.channels[0].read_burst_size = 2
        dma_instance.channels[0].read_request = dma.ChannelRequest.SPIFI_REQUEST
        dma_instance.channels[0].read_ack = dma.ChannelAck.DISABLE

        dma_instance.channels[0].write_mode = dma.ChannelMode.PERIPHERY
        dma_instance.channels[0].write_increment = dma.ChannelIncrement.DISABLE
        dma_instance.channels[0].write_size = dma.ChannelSize.WORD
        dma_instance.channels[0].write_burst_size = 2
        dma_instance.channels[0].write_request = dma.ChannelRequest.SPIFI_REQUEST
        dma_instance.channels[0].write_ack = dma.ChannelAck.DISABLE

        dma_instance.channels[1].write_buffer = 0

        dma_instance.channels[1].channel = dma.ChannelIndex.CHANNEL_1
        dma_instance.channels[1].priority = dma.ChannelPriority.VERY_HIGH

        dma_instance.channels[1].write_mode = dma.ChannelMode.MEMORY
        dma_instance.channels[1].write_increment = dma.ChannelIncrement.ENABLE
        dma_instance.channels[1].write_size = dma.ChannelSize.WORD
        dma_instance.channels[1].write_burst_size = 2
        dma_instance.channels[1].write_request = dma.ChannelRequest.SPIFI_REQUEST
        dma_instance.channels[1].write_ack = dma.ChannelAck.DISABLE

        dma_instance.channels[1].read_mode = dma.ChannelMode.PERIPHERY
        dma_instance.channels[1].read_increment = dma.ChannelIncrement.DISABLE
        dma_instance.channels[1].read_size = dma.ChannelSize.WORD
        dma_instance.channels[1].read_burst_size = 2
        dma_instance.channels[1].read_request = dma.ChannelRequest.SPIFI_REQUEST
        dma_instance.channels[1].read_ack = dma.ChannelAck.DISABLE

        return dma_instance
