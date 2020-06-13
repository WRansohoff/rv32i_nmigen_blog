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

  // Set GPIO pins 39-41 to output mode.
  GPIO->P3 |= ( ( 2 << GPIO39_O ) |
                ( 2 << GPIO40_O ) |
                ( 2 << GPIO41_O ) );

  // Endlessly increment a register, occasionally toggling
  // the on-board LEDs.
  int counter = 0;
  while( 1 ) {
    if( ( ( counter >> 10 ) & 1 ) == 1 ) {
      GPIO->P3 ^= ( 1 << GPIO39_O );
    }
    if( ( ( counter >> 11 ) & 1 ) == 1 ) {
      GPIO->P3 ^= ( 1 << GPIO40_O );
    }
    if( ( ( counter >> 12 ) & 1 ) == 1 ) {
      GPIO->P3 ^= ( 1 << GPIO41_O );
    }
    ++counter;
  }
  return 0; // lol
}
