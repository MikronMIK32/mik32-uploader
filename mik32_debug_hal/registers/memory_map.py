# --------------------------
# DMA register offset
# --------------------------
from enum import Enum


DMA_REGS = 0x00040000
DMA_CONTROL = DMA_REGS + 0x40

DMA_CHANNEL_SIZEOF = 0x4 * 4


def DMA_CHANNEL_DESTINATION(i):
    return DMA_REGS + i*DMA_CHANNEL_SIZEOF + 0x4*0


def DMA_CHANNEL_SOURCE(i):
    return DMA_REGS + i*DMA_CHANNEL_SIZEOF + 0x4*1


def DMA_CHANNEL_LEN(i):
    return DMA_REGS + i*DMA_CHANNEL_SIZEOF + 0x4*2


def DMA_CHANNEL_CONFIG(i):
    return DMA_REGS + i*DMA_CHANNEL_SIZEOF + 0x4*3


# --------------------------
# SPIFI register offset
# --------------------------
SPIFI_REGS = 0x00070000

SPIFI_CONFIG_CTRL = SPIFI_REGS + 0x000
SPIFI_CONFIG_CMD = SPIFI_REGS + 0x004
SPIFI_CONFIG_ADDR = SPIFI_REGS + 0x008
SPIFI_CONFIG_IDATA = SPIFI_REGS + 0x00C
SPIFI_CONFIG_CLIMIT = SPIFI_REGS + 0x010
SPIFI_CONFIG_DATA32 = SPIFI_REGS + 0x014
SPIFI_CONFIG_MCMD = SPIFI_REGS + 0x018
SPIFI_CONFIG_STAT = SPIFI_REGS + 0x01C


# --------------------------
# PM register offset
# --------------------------


PM_REGS = 0x000050000

PM_Clk_AHB_Set_OFFSET = PM_REGS + 0x0C
PM_Clk_APB_M_Set_OFFSET = PM_REGS + 0x14
PM_Clk_APB_P_Set_OFFSET = PM_REGS + 0x1C


# --------------------------
# WU register offset
# --------------------------
WU_REGS = 0x00060000

WU_CLOCKS_BU_OFFSET = WU_REGS + 0x10


# --------------------------
# GPIO register offset
# --------------------------
PAD_CONFIG_REGS = 0x00050C00

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
