// RISC-V Compliance IO Test Header File
// Target: 'Tubul' RV32I microcontroller core.

#ifndef _COMPLIANCE_IO_H
#define _COMPLIANCE_IO_H

// No I/O is available yet.
#define RVTEST_IO_INIT
#define RVTEST_IO_WRITE_STR( _R, _STR )
#define RVTEST_IO_CHECK()
// No floating point units are available.
#define RVTEST_IO_ASSERT_SFPR_EQ( _F, _R, _I )
#define RVTEST_IO_ASSERT_DFPR_EQ( _D, _R, _I )

// Assert that a general-purpose register has a specified value.
// Use the 'TEST_CASE' logic from 'riscv-tests'.
#define RVTEST_IO_ASSERT_GPR_EQ( _G, _R, _I ) \
  li  _G, MASK_XLEN( _I );                    \
  bne _R, _G, fail;

#endif
