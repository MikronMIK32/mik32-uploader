# --------------------------
# EEPROM register fields
# --------------------------

# EECON
EECON_EX_S = 0
EECON_OP_S = 1
EECON_WRBEH_S = 3
EECON_APBNWS_S = 5
EECON_DISECC_S = 6
EECON_BWE_S = 7
EECON_IESERR_S = 8

# EESTA
EESTA_BSY_S = 0
EESTA_SERR_S = 1

# NCYCRL
NCYCRL_N_LD_S = 0
NCYCRL_N_R_1_S = 8
NCYCRL_N_R_2_S = 16

# --------------------------
# EEPROM codes
# --------------------------
OP_RD = 0
OP_ER = 1
OP_PR = 2

BEH_EVEN = 1
BEH_ODD = 2
BEH_GLOB = 3

EEPROM_PAGE_MASK = 0x1F80