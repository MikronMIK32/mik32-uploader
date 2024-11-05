
OUTPUT_FORMAT("elf32-littleriscv", "elf32-littleriscv", "elf32-littleriscv")
OUTPUT_ARCH(riscv)

ENTRY(_start)


MEMORY {
  ram (RWX): ORIGIN = 0x02000000, LENGTH = 16K
}

STACK_SIZE = 1024;

CL_SIZE = 16;

REGION_ALIAS("REGION_TEXT", ram);
REGION_ALIAS("REGION_RAM", ram);

INCLUDE sections.lds
