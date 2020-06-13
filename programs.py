from isa import *

# "Infinite Loop" program: I think this is the simplest error-free
# application that you could write, equivalent to "while(1){};".
loop_rom = rom_img( [ JAL( 1, 0x00000 ) ] )

# Expected runtime values for the "Infinite Loop" program.
# Since the application only contains a single 'jump' instruction,
# we can expect the PC to always equal 0 and r1 to hold 0x04 (the
# 'return PC' value) after the first 'jump' instruction is executed.
loop_exp = {
  0: [ { 'r': 'pc', 'e': 0x00000000 } ],
  1: [
       { 'r': 'pc', 'e': 0x00000000 },
       { 'r': 1,   'e': 0x00000004 }
     ],
  2: [
       { 'r': 'pc', 'e': 0x00000000 },
       { 'r': 1,   'e': 0x00000004 }
     ],
  'end': 2
}

# "Run from RAM" program: Make sure that the CPU can jump between
# RAM and ROM memory spaces.
ram_rom = rom_img ( [
  # Load the starting address of the 'RAM program' into r1.
  LI( 1, 0x20000004 ),
  # Initialize the 'RAM program'.
  LI( 2, 0x20000000 ),
  LI( 3, 0xDEADBEEF ), SW( 2, 3, 0x000 ),
  LI( 3, LITTLE_END( ADDI( 7, 0, 0x0CA ) ) ), SW( 2, 3, 0x004 ),
  LI( 3, LITTLE_END( SLLI( 8, 7, 15 ) ) ), SW( 2, 3, 0x008 ),
  LI( 3, LITTLE_END( JALR( 5, 4, 0x000 ) ) ), SW( 2, 3, 0x00C ),
  # Jump to RAM.
  JALR( 4, 1, 0x000 ),
  # (This is where the program should jump back to.)
  ADDI( 9, 0, 0x123 ),
  # Done; infinite loop.
  JAL( 1, 0x00000 )
] )

# Expected runtime values for the "Run from RAM" test program.
ram_exp = {
  # Starting state: PC = 0 (ROM).
  0:  [ { 'r': 'pc', 'e': 0x00000000 } ],
  # The next 2 instructions should set r1 = 0x20000004
  2:  [ { 'r': 1, 'e': 0x20000004 } ],
  # The next 14 instructions load the short 'RAM program'.
  16: [
        { 'r': 2, 'e': 0x20000000 },
        { 'r': 'RAM%d'%( 0x00 ), 'e': 0xDEADBEEF },
        { 'r': 'RAM%d'%( 0x04 ),
          'e': LITTLE_END( ADDI( 7, 0, 0x0CA ) ) },
        { 'r': 'RAM%d'%( 0x08 ),
          'e': LITTLE_END( SLLI( 8, 7, 15 ) ) },
        { 'r': 'RAM%d'%( 0x0C ),
          'e': LITTLE_END( JALR( 5, 4, 0x000 ) ) }
      ],
  # The next instruction should jump to RAM.
  17: [
        { 'r': 'pc', 'e': 0x20000004 },
        { 'r': 4, 'e': 0x00000044 }
      ],
  # The next two instructions should set r7, r8.
  19: [
        { 'r': 'pc', 'e': 0x2000000C },
        { 'r': 7, 'e': 0x000000CA },
        { 'r': 8, 'e': 0x00650000 }
      ],
  # The next instruction should jump back to ROM address space.
  20: [ { 'r': 'pc', 'e': 0x00000044 } ],
  # Finally, one more instruction should set r9.
  21: [ { 'r': 9, 'e': 0x00000123 } ],
  'end': 22
}

loop_test    = [ 'inifinite loop test', 'cpu_loop',
                 loop_rom, [], loop_exp ]
ram_pc_test  = [ 'run from RAM test', 'cpu_ram',
                 ram_rom, [], ram_exp ]
