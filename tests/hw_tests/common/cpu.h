#ifndef __CPU_DEVICE
#define __CPU_DEVICE

#include <stdint.h>

// Device header file:
// GPIO struct: 4 registers, 16 pins per register.
typedef struct
{
  volatile uint32_t P1;
  volatile uint32_t P2;
  volatile uint32_t P3;
  volatile uint32_t P4;
} GPIO_TypeDef;
// GPIO multiplexer strut: 7 registers, 8 pins per register.
typedef struct
{
  volatile uint32_t CFG1;
  volatile uint32_t CFG2;
  volatile uint32_t CFG3;
  volatile uint32_t CFG4;
  volatile uint32_t CFG5;
  volatile uint32_t CFG6;
  volatile uint32_t CFG7;
} IOMUX_TypeDef;
// Pulse Width Modulation struct: only one register.
typedef struct
{
  // "Control register": Holds the 'compare' and 'max' values
  // which determine the PWM duty cycle.
  volatile uint32_t CR;
} PWM_TypeDef;

// Peripheral address definitions
#define GPIO  ( ( GPIO_TypeDef * )  0x40000000 )
#define IOMUX ( ( IOMUX_TypeDef * ) 0x40010000 )
#define PWM1  ( ( PWM_TypeDef * )   0x40020000 )
#define PWM2  ( ( PWM_TypeDef * )   0x40020100 )
#define PWM3  ( ( PWM_TypeDef * )   0x40020200 )

// GPIO pin address offsets.
// (not every pin is an I/O pin)
#define GPIO2_O  ( 4 )
#define GPIO3_O  ( 6 )
#define GPIO4_O  ( 8 )
#define GPIO9_O  ( 18 )
#define GPIO11_O ( 22 )
#define GPIO12_O ( 24 )
#define GPIO13_O ( 26 )
#define GPIO18_O ( 4 )
#define GPIO19_O ( 6 )
#define GPIO21_O ( 10 )
#define GPIO23_O ( 14 )
#define GPIO25_O ( 18 )
#define GPIO26_O ( 20 )
#define GPIO27_O ( 22 )
#define GPIO31_O ( 30 )
#define GPIO32_O ( 0 )
#define GPIO33_O ( 2 )
#define GPIO34_O ( 4 )
#define GPIO35_O ( 6 )
#define GPIO36_O ( 8 )
#define GPIO37_O ( 10 )
#define GPIO38_O ( 12 )
#define GPIO39_O ( 14 )
#define GPIO40_O ( 16 )
#define GPIO41_O ( 18 )
#define GPIO42_O ( 20 )
#define GPIO43_O ( 22 )
#define GPIO44_O ( 24 )
#define GPIO45_O ( 26 )
#define GPIO46_O ( 28 )
#define GPIO47_O ( 30 )
#define GPIO48_O ( 0 )

// GPIO multiplexer pin configuration values.
#define IOMUX_GPIO ( 0x0 )
#define IOMUX_PWM1 ( 0x1 )
#define IOMUX_PWM2 ( 0x2 )
#define IOMUX_PWM3 ( 0x3 )
// GPIO multiplexer pin configuration offsets.
#define IOMUX2_O   ( 8 )
#define IOMUX3_O   ( 12 )
#define IOMUX4_O   ( 16 )
#define IOMUX9_O   ( 4 )
#define IOMUX11_O  ( 12 )
#define IOMUX12_O  ( 16 )
#define IOMUX13_O  ( 20 )
#define IOMUX18_O  ( 8 )
#define IOMUX19_O  ( 12 )
#define IOMUX21_O  ( 20 )
#define IOMUX23_O  ( 28 )
#define IOMUX25_O  ( 4 )
#define IOMUX26_O  ( 8 )
#define IOMUX27_O  ( 12 )
#define IOMUX31_O  ( 28 )
#define IOMUX32_O  ( 0 )
#define IOMUX33_O  ( 4 )
#define IOMUX34_O  ( 8 )
#define IOMUX35_O  ( 12 )
#define IOMUX36_O  ( 16 )
#define IOMUX37_O  ( 20 )
#define IOMUX38_O  ( 24 )
#define IOMUX39_O  ( 28 )
#define IOMUX40_O  ( 0 )
#define IOMUX41_O  ( 4 )
#define IOMUX42_O  ( 8 )
#define IOMUX43_O  ( 12 )
#define IOMUX44_O  ( 16 )
#define IOMUX45_O  ( 20 )
#define IOMUX46_O  ( 24 )
#define IOMUX47_O  ( 28 )
#define IOMUX48_O  ( 0 )

// PWM peripheral control register offsets and masks.
#define PWM_CR_CMP_O ( 0 )
#define PWM_CR_CMP_M ( 0xFF << PWM_CR_CMP_O )

#endif
