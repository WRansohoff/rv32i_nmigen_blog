#
# Test that the 'MINSTRET' CSR is writable, and ticks up once per
# instruction. Some tests just test that the value is in the right
# range, in the hopes of accounting for assembler differences.
#
# Note: This is not part of the standard `riscv-tests`, and it
# may not be an accurate reflection of the specification.
#

#include "riscv_test_macros.h"
#include "compliance_test.h"
#include "compliance_io.h"

RV_COMPLIANCE_RV32M
RV_COMPLIANCE_CODE_BEGIN
  RVTEST_IO_INIT
  li TESTNUM, 1
  RVTEST_IO_ASSERT_GPR_EQ(x31, x0, 0x00000000)

  # Make sure that MINSTRET reflects that a number of instructions
  # ran during the startup code sequence.
  li TESTNUM, 2
  csrr a2, minstret;
  slti a3, a2, 5
  RVTEST_IO_ASSERT_GPR_EQ( x31, a3, 0 )

  # Clear MINSTRET, and make sure that it equals 1 after the
  # following 'CSR read' instruction.
  li TESTNUM, 3
  li a1, 0xFFFFFFFF
  csrc minstret, a1
  csrr a3, minstret
  RVTEST_IO_ASSERT_GPR_EQ( x31, a3, 1 )

  # Clear MINSTRET, and make sure that it equals 1 after the
  # following 'CSR read and clear' instruction.
  li TESTNUM, 4
  csrc minstret, a1
  csrrc a3, minstret, a1
  RVTEST_IO_ASSERT_GPR_EQ( x31, a3, 1 )

  # Ensure that MINSTRET ticks up with the number of instructions
  # which have been execut- uh, "retired". They're on a farm upstate.
  csrc minstret, a1
  nop
  nop
  csrr a3, minstret
  RVTEST_IO_ASSERT_GPR_EQ( x31, a3, 3 )
  nop
  nop
  nop
  csrr a3, minstret
  RVTEST_IO_ASSERT_GPR_EQ( x31, a3, 9 )

  RV_COMPLIANCE_HALT

RV_COMPLIANCE_CODE_END

  .data
RV_COMPLIANCE_DATA_BEGIN

RV_COMPLIANCE_DATA_END
