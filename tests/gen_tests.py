import os
import subprocess
import sys

od = 'riscv32-unknown-elf-objdump'
test_path = "%s/"%( os.path.dirname( sys.argv[ 0 ] ) )

# Helper method to get raw hex out of an object file memory section
# This basically returns the compiled machine code for one
# of the RISC-V assembly test files.
def get_section_hex( op, sect, in_dir ):
  hdump = subprocess.run( [ od, '-s', '-j', sect,
                            './%s/%s/%s'
                            %( test_path, in_dir, op ) ],
                          stdout = subprocess.PIPE
                        ).stdout.decode( 'utf-8' )
  hexl = []
  hls = hdump.split( '\n' )[ 4: ]
  for l in hls:
    hl = l.strip()
    while '  ' in hl:
      hl = hl.replace( '  ', ' ' )
    toks = hl.split( ' ' )
    if len( toks ) < 6:
      break
    hexl.append( '0x%s'%toks[ 1 ].upper() )
    hexl.append( '0x%s'%toks[ 2 ].upper() )
    hexl.append( '0x%s'%toks[ 3 ].upper() )
    hexl.append( '0x%s'%toks[ 4 ].upper() )
  return hexl

# Helper method to write a Python file containing a simulated ROM
# test image and testbench condition to verify that it ran correclty.
def write_py_tests( op, hext, hexd, out_dir ):
  instrs = len( hext )
  opp = ''
  opn = op.upper() + ' compliance'
  while len( opp ) < ( 13 - len( op ) ):
    opp = opp + ' '
  py_fn = './%s/%s/rv32i_%s.py'%( test_path, out_dir, op )
  with open( py_fn, 'w' ) as py:
    print( 'Generating %s tests...'%op, end = '' )
    # Write imports and headers.
    py.write( 'from nmigen import *\r\n'
              'from rom import *\r\n'
              '\r\n'
              '###########################################\r\n'
              '# rv32ui %s instruction tests: %s#\r\n'
              '###########################################\r\n'
              '\r\n'%( op.upper(), opp ) )
    # Write the ROM image.
    py.write( '# Simulated ROM image:\r\n'
              '%s_rom = rom_img( ['%op )
    for x in range( len( hext ) ):
      if ( x % 4 ) == 0:
        py.write( '\r\n  ' )
      py.write( '%s'%hext[ x ] )
      if x < ( len( hext ) - 1 ):
        py.write( ', ' )
    py.write( '\r\n] )\r\n' )
    # Write the inirialized RAM values.
    py.write( '\r\n# Simulated initialized RAM image:\r\n'
              '%s_ram = ram_img( ['%op )
    for x in range( len( hexd ) ):
      if ( x % 4 ) == 0:
        py.write( '\r\n  ' )
      py.write( '%s'%hexd[ x ] )
      if x < ( len( hexd ) - 1 ):
        py.write( ', ' )
    py.write( '\r\n] )\r\n' )
    # Run most tests for 2x the number of instructions to account
    # for jumps, except for the 'fence' test which uses 3x because
    # it has a long 'prefetcher test' which counts down from 100.
    num_instrs = ( instrs * 3 ) if 'fence' in op else ( instrs * 2 )
    # Write the 'expected' value for the testbench to check
    # after tests finish.
    py.write( "\r\n# Expected 'pass' register values.\r\n"
              "%s_exp = {\r\n"
              "  %d: [ { 'r': 17, 'e': 93 }, { 'r': 10, 'e': 0 } ],"
              "  'end': %d\r\n}\r\n"%( op, num_instrs, num_instrs ) )
    # Write the test struct.
    py.write( "\r\n# Collected test program definition:\r\n%s_test = "
              "[ '%s tests', 'cpu_%s', %s_rom, %s_ram, %s_exp ]"
              %( op, opn, op, op, op, op ) )
  print( "Done!" )

# Ensure that the test ROM directories exists.
if not os.path.exists( './%s/test_roms'%test_path ):
  os.makedirs( './%s/test_roms'%test_path )
# Run 'make clean && make' to re-compile the files.
subprocess.run( [ 'make', 'clean' ],
                cwd = './%s/rv32i_compliance/'%test_path )
subprocess.run( [ 'make' ],
                cwd = './%s/rv32i_compliance/'%test_path )
# Process all compiled test files.
for fn in os.listdir( './%s/rv32i_compliance'%test_path ):
  if fn[ -1 ] == 'o':
    op = fn[ :-2 ]
    # Get machine code instructions for the operation's tests.
    hext = get_section_hex( '%s.o'%op, '.text', 'rv32i_compliance' )
    # Get initialized RAM data for the operation's tests.
    hexd = get_section_hex( '%s.o'%op, '.data', 'rv32i_compliance' )
    # Write a Python file with the test program image.
    write_py_tests( op[ 2 : -3 ].lower(), hext, hexd, 'test_roms' )
