
SECTIONS {
    .text ORIGIN(REGION_TEXT) : {
        PROVIDE(__TEXT_START__ = .);
        *crt0.o(.text .text.*)
        *(.text.smallsysteminit)
        *(.text.SmallSystemInit)
        . = ORIGIN(REGION_TEXT) + 0xC0;
        KEEP(*crt0.o(.trap_text))

        *(.text)
        *(.text.*)
        *(.rodata)
        *(.rodata.*)      
        . = ALIGN(CL_SIZE);
        PROVIDE(__TEXT_END__ = .);
    } >REGION_TEXT 

    .data : 
    AT( __TEXT_END__ ) {
        PROVIDE(__DATA_START__ = .);
        _gp = .;
        *(.srodata.cst16) *(.srodata.cst8) *(.srodata.cst4) *(.srodata.cst2) *(.srodata*)
        *(.sdata .sdata.* .gnu.linkonce.s.*)
        *(.data .data.*)
        . = ALIGN(CL_SIZE);
        PROVIDE(__DATA_END__ = .);
    } >REGION_RAM
    
    __DATA_IMAGE_START__ = LOADADDR(.data);
    __DATA_IMAGE_END__ = LOADADDR(.data) + SIZEOF(.data);

    /* thread-local data segment */
    .tdata : {
        PROVIDE(_tls_data = .);
        PROVIDE(_tdata_begin = .);
        *(.tdata .tdata.*)
        PROVIDE(_tdata_end = .);
        . = ALIGN(CL_SIZE);
    } >REGION_RAM

    .tbss : {
        PROVIDE(__BSS_START__ = .);
        *(.tbss .tbss.*)
        . = ALIGN(CL_SIZE);
        PROVIDE(_tbss_end = .);
    } >REGION_RAM

    /* bss segment */
    .sbss : {
        *(.sbss .sbss.* .gnu.linkonce.sb.*)
        *(.scommon)
    } >REGION_RAM

    .bss : {
        *(.bss .bss.*)
        *(COMMON)
        . = ALIGN(CL_SIZE);
        PROVIDE(__BSS_END__ = .);
    } >REGION_RAM

    /* Code intended to be copied to REGION_RAM before execution */
    .ram_text : 
    AT( ALIGN(__DATA_IMAGE_END__, CL_SIZE) ) {
        PROVIDE(__RAM_TEXT_START__ = .);
        *(.ram_text)
        . = ALIGN(CL_SIZE);
        PROVIDE(__RAM_TEXT_END__ = .);
    } > REGION_RAM
    
    __RAM_TEXT_IMAGE_START__ = LOADADDR(.ram_text);
    __RAM_TEXT_IMAGE_END__ = LOADADDR(.ram_text) + SIZEOF(.ram_text);
    ASSERT(__RAM_TEXT_IMAGE_END__ < ORIGIN(REGION_TEXT) + LENGTH(REGION_TEXT), "REGION_TEXT segment overflows")

    ASSERT(__RAM_TEXT_END__ < ORIGIN(REGION_RAM) + LENGTH(REGION_RAM) - STACK_SIZE, "REGION_RAM section overflows")

    _end = .;
    PROVIDE(__end = .);

    BUFFER4K_SIZE = 4K;

    .buffer4k ORIGIN(REGION_RAM) + 8K : {
        FILL(0);
        PROVIDE(__BUFFER4K__END__ = .);
        PROVIDE(BUFFER4K = .);
        . += BUFFER4K_SIZE;
        PROVIDE(BUFFER_STATUS = .);
        . += 4;
        PROVIDE(__BUFFER4K__END__ = .);
    } >REGION_RAM

    /* End of uninitalized data segement */

    .stack ORIGIN(REGION_RAM) + LENGTH(REGION_RAM) - STACK_SIZE : {
        FILL(0);
        PROVIDE(__STACK_START__ = .);
        . += STACK_SIZE;
        PROVIDE(__C_STACK_TOP__ = .);
        PROVIDE(__STACK_END__ = .);
    } >REGION_RAM

    /DISCARD/ : {
        *(.eh_frame .eh_frame.*)
    }
}