#
# Test that the 'MCYCLE' CSR is writable, and ticks up more than
# once per instruction. Individual clock cycles are not counted,
# out of an effort to make the tests less fragile.
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

  # Make sure that MCYCLE has ticked a number of times
  # (>10 ticks) over the course of the startup code.
  li TESTNUM, 2
  csrr a2, mcycle
  slti a3, a2, 10
  RVTEST_IO_ASSERT_GPR_EQ( x31, a3, 0 )

  # Clear MCYCLE, and make sure that it is small (<10).
  # It won't be zero, because there is more than one cycle between
  # instructions and CSR reads return the previous value.
  li a1, 0xFFFFFFFF
  li TESTNUM, 3
  csrc mcycle, a1
  csrr a2, mcycle
  slti a3, a2, 10
  RVTEST_IO_ASSERT_GPR_EQ( x31, a3, 1 )

  # Ensure that MCYCLE increases over time.
  li TESTNUM, 3
  csrr a1, mcycle
  nop
  nop
  nop
  csrr a2, mcycle
  slt a3, a1, a2
  RVTEST_IO_ASSERT_GPR_EQ( x31, a3, 1 )

  RV_COMPLIANCE_HALT

RV_COMPLIANCE_CODE_END

  .data
RV_COMPLIANCE_DATA_BEGIN

RV_COMPLIANCE_DATA_END
