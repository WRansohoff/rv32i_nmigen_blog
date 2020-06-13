/* Linker script for a minimal simulated RV32I RISC-V CPU */
OUTPUT_ARCH( "riscv" )
ENTRY( _start )

MEMORY
{
  ROM   (rx)  : ORIGIN = 0x00000000, LENGTH = 1M
  RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 4K
}

SECTIONS
{
  __stack_size = DEFINED(__stack_size) ? __stack_size : 128;

  .text :
  {
    KEEP (*(SORT_NONE(.reset_handler)))
    KEEP (*(SORT_NONE(.vector_table)))
    *(.rodata .rodata.*)
    *(.srodata .srodata.*)
    *(.text .text.*)
    *(.tohost .tohost.*)
  } >ROM

  . = ALIGN(4);
  PROVIDE (__etext = .);
  PROVIDE (_etext = .);
  PROVIDE (etext = .);
  _sidata = .;
  .data : AT( _sidata )
  {
    . = . + 4;
    _sdata = .;
    *(.rdata)
    *(.data .data.*)
    *(.sdata .sdata.*)
    . = ALIGN(4);
    _edata = .;
  } >RAM

  PROVIDE( _edata = . );
  PROVIDE( edata = . );
  PROVIDE( _fbss = . );
  PROVIDE( __bss_start = . );
  .bss :
  {
    _sbss = .;
    *(.sbss*)
    *(.bss .bss.*)
    *(COMMON)
    . = ALIGN(4);
    _ebss = .;
  } >RAM

  . = ALIGN(8);
  PROVIDE( _end = . );
  PROVIDE( end = . );
  .stack ORIGIN(RAM) + LENGTH(RAM) - __stack_size :
  {
    PROVIDE( _heap_end = . );
    . = __stack_size;
    PROVIDE( _sp = . );
  } >RAM
}
