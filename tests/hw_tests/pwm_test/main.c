// Standard library includes.
#include <stdint.h>
#include <string.h>

// Device header files
#include "encoding.h"
#include "cpu.h"

// Pre-defined memory locations for program initialization.
extern uint32_t _sidata, _sdata, _edata, _sbss, _ebss;

// 'main' method which gets called from the boot code.
int main( void ) {
  // Copy initialized data from .sidata (Flash) to .data (RAM)
  memcpy( &_sdata, &_sidata, ( ( void* )&_edata - ( void* )&_sdata ) );
  // Clear the .bss RAM section.
  memset( &_sbss, 0x00, ( ( void* )&_ebss - ( void* )&_sbss ) );

  // Connect pins 39-41 to PWM peripherals 1-3.
  IOMUX->CFG5 |= ( IOMUX_PWM1 << IOMUX39_O );
  IOMUX->CFG6 |= ( ( IOMUX_PWM2 << IOMUX40_O ) |
                   ( IOMUX_PWM3 << IOMUX41_O ) );

  // Increment a counter and set the PWM 'compare' values from it.
  int counter = 0;
  int gdir = 1;
  int bdir = -1;
  int rdir = 1;
  int g = 0;
  int b = 10;
  int r = 20;
  while( 1 ) {
    ++counter;
    // Don't increment color values on every tick, so the
    // color transitions are visible.
    if ( ( ( counter & 0xFF ) == 0 ) && ( counter & 0x100 ) ) {
      g += gdir;
      b += bdir;
      r += rdir;
      // Don't go all the way up to max brightness.
      if ( ( g == 0x1F ) || ( g == 0 ) ) { gdir = -gdir; }
      if ( ( b == 0x1F ) || ( b == 0 ) ) { bdir = -bdir; }
      if ( ( r == 0x1F ) || ( r == 0 ) ) { rdir = -rdir; }
      // Apply the new colors.
      PWM1->CR = g;
      PWM2->CR = b;
      PWM3->CR = r;
    }
  }
  return 0; // lol
}
