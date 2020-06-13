// RISC-V Compliance Test Header File

#ifndef _COMPLIANCE_TEST_H
#define _COMPLIANCE_TEST_H

#include "riscv_test.h"

// Just use the 'TEST_PASSFAIL' macro from
// the 'riscv-tests' repository for now.
#undef RVTEST_PASS
#define RVTEST_PASS              \
        fence;                   \
        li a7, 93;               \
        li a0, 0;                \
        j pass;

#undef RVTEST_FAIL
#define RVTEST_FAIL              \
        fence;                   \
        li a7, 93;               \
        li a0, 0xBAD;            \
        j fail;

#define RV_COMPLIANCE_HALT       \
  pass:                          \
    RVTEST_PASS                  \
  fail:                          \
    RVTEST_FAIL;                 \

#define RV_COMPLIANCE_RV32M      \
  RVTEST_RV32M                   \

#define RV_COMPLIANCE_CODE_BEGIN \
  RVTEST_CODE_BEGIN              \

#define RV_COMPLIANCE_CODE_END   \
  RVTEST_CODE_END                \

#define RV_COMPLIANCE_DATA_BEGIN \
  RVTEST_DATA_BEGIN              \

#define RV_COMPLIANCE_DATA_END   \
  RVTEST_DATA_END                \

#endif
