# --------------------------
# PM register offset
# --------------------------
from enum import Enum
from tclrpc import OpenOcdTclRpc


class MIK32_Version(Enum):
    MIK32V0 = "MIK32V0"
    MIK32V2 = "MIK32V2"

    def __str__(self):
        return self.value


PAD_CONFIG_BASE_ADDRESS = 0x00050C00

class PAD_CONFIG_REGS_V0(Enum):
    PORT_0_CFG = 0x00
    PORT_1_CFG = 0x04
    PORT_2_CFG = 0x08
    PORT_0_DS  = 0x0C
    PORT_1_DS  = 0x10
    PORT_2_DS  = 0x14
    PORT_0_PUD = 0x18
    PORT_1_PUD = 0x1C
    PORT_2_PUD = 0x20

class PAD_CONFIG_REGS_V2(Enum):
    PORT_0_CFG = 0x00
    PORT_0_DS  = 0x04
    PORT_0_PUD = 0x08
    PORT_1_CFG = 0x0C
    PORT_1_DS  = 0x10
    PORT_1_PUD = 0x14
    PORT_2_CFG = 0x18
    PORT_2_DS  = 0x1C
    PORT_2_PUD = 0x20


port2_value = 0


def gpio_init(openocd: OpenOcdTclRpc, version: MIK32_Version):

    port2_addr = 0
    if version == MIK32_Version.MIK32V0:
        port2_addr = PAD_CONFIG_BASE_ADDRESS + PAD_CONFIG_REGS_V0.PORT_2_CFG.value
    elif version == MIK32_Version.MIK32V2:
        port2_addr = PAD_CONFIG_BASE_ADDRESS + PAD_CONFIG_REGS_V2.PORT_2_CFG.value
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
        port2_addr = PAD_CONFIG_BASE_ADDRESS + PAD_CONFIG_REGS_V0.PORT_2_CFG.value
    elif version == MIK32_Version.MIK32V2:
        port2_addr = PAD_CONFIG_BASE_ADDRESS + PAD_CONFIG_REGS_V2.PORT_2_CFG.value
    else:
        return

    openocd.write_word(port2_addr, port2_value)
