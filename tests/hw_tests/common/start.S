#include "encoding.h"

/* Reset handler. */
.global _start
.type _start, %object
.section .reset_handler,"a",%progbits
_start:
  // Ensure that interrupts are disabled.
  csrrci x0, mstatus, MSTATUS_MIE
  // Set the stack pointer.
  la sp, _sp
  // Set the default vector table address.
  la t0, vtable
  csrrw x0, mtvec, t0
  // Set vectored interrupt mode.
  csrrsi x0, mtvec, 0x1
  // Call main(0, 0) in case 'argc' and 'argv' are present.
  li a0, 0
  li a1, 1
  call main


/*
 * Main vector table entries.
 * Hold entries for supported vectored exception and interrupts.
 * TODO: Have the CPU jump to the addresses instead of running them.
 */
.global vtable
.type vtable, %object
.section .vector_table,"a",%progbits
vtable:
  // 0: Misaligned instruction address fault.
  J trap_imis
  .word 0
  .word 0
  // 3: Breakpoint trap.
  J trap_ebreak
  // 4: Misaligned load address fault.
  J trap_lmis
  .word 0
  // 6: Misaligned store address fault.
  J trap_smis
  .word 0
  .word 0
  .word 0
  .word 0
  // 11: Environment call from M-mode trap.
  J trap_ecall

  /*
   * Weak aliases to point each exception hadnler to the
   * 'default_interrupt_handler', unless the application defines
   * a function with the same name to override the reference.
   */
  .weak trap_imis
  .set  trap_imis,default_interrupt_handler
  .weak trap_ebreak
  .set  trap_ebreak,default_interrupt_handler
  .weak trap_lmis
  .set  trap_lmis,default_interrupt_handler
  .weak trap_smis
  .set  trap_smis,default_interrupt_handler
  .weak trap_ecall
  .set  trap_ecall,default_interrupt_handler

/*
 * A 'default' interrupt handler, in case an interrupt triggers
 * without a handler being defined.
 */
.section .text.default_interrupt_handler,"ax",%progbits
default_interrupt_handler:
    default_interrupt_loop:
      j default_interrupt_loop
