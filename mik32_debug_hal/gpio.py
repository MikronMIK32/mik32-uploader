from enum import Enum
from tclrpc import OpenOcdTclRpc
import mik32_debug_hal.registers.memory_map as mem_map


class MIK32_Version(Enum):
    MIK32V0 = "MIK32V0"
    MIK32V2 = "MIK32V2"

    def __str__(self):
        return self.value


port2_value = 0


def gpio_init(openocd: OpenOcdTclRpc, version: MIK32_Version):

    port2_addr = 0
    if version == MIK32_Version.MIK32V0:
        port2_addr = mem_map.PAD_CONFIG_REGS + mem_map.PAD_CONFIG_REGS_V0.PORT_2_CFG.value
    elif version == MIK32_Version.MIK32V2:
        port2_addr = mem_map.PAD_CONFIG_REGS + mem_map.PAD_CONFIG_REGS_V2.PORT_2_CFG.value
    else:
        return

    openocd.halt()
    port2_value = openocd.read_memory(port2_addr, 32, 1)[0]

    port2_value_updated = port2_value

    port2_value_updated &= 0xF000

    if version == MIK32_Version.MIK32V0:
        port2_value_updated |= 0x000
    elif version == MIK32_Version.MIK32V2:
        port2_value_updated |= 0x555
    else:
        return
    

    openocd.write_word(port2_addr, port2_value_updated)

    openocd.write_word(port2_addr + 8, 0x0500)


def gpio_deinit(openocd: OpenOcdTclRpc, version: MIK32_Version):

    if version == MIK32_Version.MIK32V0:
        port2_addr = mem_map.PAD_CONFIG_REGS + mem_map.PAD_CONFIG_REGS_V0.PORT_2_CFG.value
    elif version == MIK32_Version.MIK32V2:
        port2_addr = mem_map.PAD_CONFIG_REGS + mem_map.PAD_CONFIG_REGS_V2.PORT_2_CFG.value
    else:
        return

    openocd.write_word(port2_addr, port2_value)
