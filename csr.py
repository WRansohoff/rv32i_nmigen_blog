from nmigen import *
from nmigen.back.pysim import *
from nmigen_boards.upduino_v2 import *
from nmigen_soc.wishbone import *
from nmigen_soc.memory import *

from isa import *

import sys
import warnings

#############################################
# 'Control and Status Registers' file.      #
# This contains logic for handling the      #
# 'system' opcode, which is used to         #
# read/write CSRs in the base ISA.          #
# CSR named constants are in `isa.py`.      #
#############################################

# Core "CSR" class, which addresses Control and Status Registers.
class CSR( Elaboratable, Interface ):
  def __init__( self ):
    # CSR function select signal.
    self.f  = Signal( 3,  reset = 0b000 )
    # Actual data to write (depends on write/set/clear function)
    self.wd = Signal( 32, reset = 0x00000000 )
    # Initialize wishbone bus interface.
    Interface.__init__( self, addr_width = 12, data_width = 32 )
    self.memory_map = MemoryMap( addr_width = self.addr_width,
                                 data_width = self.data_width,
                                 alignment = 0 )

    # Initialize required CSR signals and constants.
    for cname, reg in CSRS.items():
      for bname, bits in reg[ 'bits' ].items():
        if 'w' in bits[ 2 ]:
          setattr( self,
                   "%s_%s"%( cname, bname ),
                   Signal( bits[ 1 ] - bits[ 0 ] + 1,
                           name = "%s_%s"%( cname, bname ),
                           reset = bits[ 3 ] ) )
        elif 'r' in bits[ 2 ]:
          setattr( self,
                   "%s_%s"%( cname, bname ),
                   Const( bits[ 3 ] ) )

  def elaborate( self, platform ):
    m = Module()

    # Read values default to 0.
    m.d.comb += self.dat_r.eq( 0 )

    with m.Switch( self.adr ):
      # Generate logic for supported CSR reads / writes.
      for cname, reg in CSRS.items():
        with m.Case( reg[ 'c_addr' ] ):
          # Assemble the read value from individual bitfields.
          for bname, bits in reg[ 'bits' ].items():
            if 'r' in bits[ 2 ]:
              m.d.comb += self.dat_r \
                .bit_select( bits[ 0 ], bits[ 1 ] - bits[ 0 ] + 1 ) \
                .eq( getattr( self, "%s_%s"%( cname, bname ) ) )
            with m.If( self.we == 1 ):
              # Writes are enabled; set new values on the next tick.
              if 'w' in bits[ 2 ]:
                m.d.sync += getattr( self, "%s_%s"%( cname, bname ) ) \
                  .eq( self.wd[ bits[ 0 ] : ( bits[ 1 ] + 1 ) ] )

    # Process 32-bit CSR write logic.
    with m.If( ( self.f[ :2 ] ) == 0b01 ):
      # 'Write' - set the register to the input value.
      m.d.comb += self.wd.eq( self.dat_w )
    with m.Elif( ( ( self.f[ :2 ] ) == 0b10 ) & ( self.dat_w != 0 ) ):
      # 'Set' - set bits which are set in the input value.
      m.d.comb +=  self.wd.eq( self.dat_w | self.dat_r )
    with m.Elif( ( ( self.f[ :2 ] ) == 0b11 ) & ( self.dat_w != 0 ) ):
      # 'Clear' - reset bits which are set in the input value.
      m.d.comb += self.wd.eq( ~( self.dat_w ) & self.dat_r )
    with m.Else():
      # Read-only operation; set write data to current value.
      m.d.comb += self.wd.eq( self.dat_r )
    return m

##################
# CSR testbench: #
##################
# Keep track of test pass / fail rates.
p = 0
f = 0

# Perform an individual CSR unit test.
def csr_ut( csr, reg, rin, cf, expected ):
  global p, f
  # Set address, write data, f.
  yield csr.adr.eq( reg )
  yield csr.dat_w.eq( rin )
  yield csr.f.eq( cf )
  # Wait a tick.
  yield Tick()
  # Check the result after combinatorial logic.
  yield Settle()
  actual = yield csr.dat_r
  if hexs( expected ) != hexs( actual ):
    f += 1
    print( "\033[31mFAIL:\033[0m CSR 0x%03X = %s (got: %s)"
           %( reg, hexs( expected ), hexs( actual ) ) )
  else:
    p += 1
    print( "\033[32mPASS:\033[0m CSR 0x%03X = %s"
           %( reg, hexs( expected ) ) )
  # Set 'rw' and wait another tick.
  yield csr.we.eq( 1 )
  yield Tick()
  yield Settle()
  # Done. Reset rsel, rin, f, rw.
  yield csr.adr.eq( 0 )
  yield csr.dat_w.eq( 0 )
  yield csr.f.eq( 0 )
  yield csr.we.eq( 0 )

# Perform some basic CSR operation tests on a fully re-writable CSR.
def csr_rw_ut( csr, reg ):
  # 'Set' with rin == 0 reads the value without writing.
  yield from csr_ut( csr, reg, 0x00000000, F_CSRRS,  0x00000000 )
  # 'Set Immediate' to set all bits.
  yield from csr_ut( csr, reg, 0xFFFFFFFF, F_CSRRSI, 0x00000000 )
  # 'Clear' to reset some bits.
  yield from csr_ut( csr, reg, 0x01234567, F_CSRRC,  0xFFFFFFFF )
  # 'Write' to set some bits and reset others.
  yield from csr_ut( csr, reg, 0x0C0FFEE0, F_CSRRW,  0xFEDCBA98 )
  # 'Write Immediate' to do the same thing.
  yield from csr_ut( csr, reg, 0xFFFFFCBA, F_CSRRWI, 0x0C0FFEE0 )
  # 'Clear Immediate' to clear all bits.
  yield from csr_ut( csr, reg, 0xFFFFFFFF, F_CSRRCI, 0xFFFFFCBA )
  # 'Clear' with rin == 0 reads the value without writing.
  yield from csr_ut( csr, reg, 0x00000000, F_CSRRC,  0x00000000 )

# Top-level CSR test method.
def csr_test( csr ):
  # Wait a tick and let signals settle after reset.
  yield Settle()
  # Print a test header.
  print( "--- CSR Tests ---" )

  # Test reading / writing 'MSTATUS' CSR. (Only 'MIE' can be written)
  yield from csr_ut( csr, CSRA_MSTATUS, 0xFFFFFFFF, F_CSRRWI, 0x00000000 )
  yield from csr_ut( csr, CSRA_MSTATUS, 0xFFFFFFFF, F_CSRRCI, 0x00000008 )
  yield from csr_ut( csr, CSRA_MSTATUS, 0xFFFFFFFF, F_CSRRSI, 0x00000000 )
  yield from csr_ut( csr, CSRA_MSTATUS, 0x00000000, F_CSRRW,  0x00000008 )
  yield from csr_ut( csr, CSRA_MSTATUS, 0x00000000, F_CSRRS,  0x00000000 )
  # Test reading / writing 'MTVEC' CSR. (R/W except 'MODE' >= 2)
  yield from csr_ut( csr, CSRA_MTVEC, 0xFFFFFFFF, F_CSRRWI, 0x00000000 )
  yield from csr_ut( csr, CSRA_MTVEC, 0xFFFFFFFF, F_CSRRCI, 0xFFFFFFFD )
  yield from csr_ut( csr, CSRA_MTVEC, 0xFFFFFFFE, F_CSRRSI, 0x00000000 )
  yield from csr_ut( csr, CSRA_MTVEC, 0x00000003, F_CSRRW,  0xFFFFFFFC )
  yield from csr_ut( csr, CSRA_MTVEC, 0x00000000, F_CSRRS,  0x00000001 )
  # Test reading / writing the 'MEPC' CSR. All bits except 0-1 R/W.
  yield from csr_ut( csr, CSRA_MEPC, 0x00000000, F_CSRRS,  0x00000000 )
  yield from csr_ut( csr, CSRA_MEPC, 0xFFFFFFFF, F_CSRRSI, 0x00000000 )
  yield from csr_ut( csr, CSRA_MEPC, 0x01234567, F_CSRRC,  0xFFFFFFFC )
  yield from csr_ut( csr, CSRA_MEPC, 0x0C0FFEE0, F_CSRRW,  0xFEDCBA98 )
  yield from csr_ut( csr, CSRA_MEPC, 0xFFFFCBA9, F_CSRRW,  0x0C0FFEE0 )
  yield from csr_ut( csr, CSRA_MEPC, 0xFFFFFFFF, F_CSRRCI, 0xFFFFCBA8 )
  yield from csr_ut( csr, CSRA_MEPC, 0x00000000, F_CSRRS,  0x00000000 )
  # Test reading / writing the 'MCAUSE' CSR.
  yield from csr_rw_ut( csr, CSRA_MCAUSE )
  # Test reading / writing the 'MTVAL' CSR.
  yield from csr_rw_ut( csr, CSRA_MTVAL )
  # Test an unrecognized CSR.
  yield from csr_ut( csr, 0x101, 0x89ABCDEF, F_CSRRW,  0x00000000 )
  yield from csr_ut( csr, 0x101, 0x89ABCDEF, F_CSRRC,  0x00000000 )
  yield from csr_ut( csr, 0x101, 0x89ABCDEF, F_CSRRS,  0x00000000 )
  yield from csr_ut( csr, 0x101, 0xFFFFCDEF, F_CSRRWI, 0x00000000 )
  yield from csr_ut( csr, 0x101, 0xFFFFCDEF, F_CSRRCI, 0x00000000 )
  yield from csr_ut( csr, 0x101, 0xFFFFCDEF, F_CSRRSI, 0x00000000 )

  # Done.
  yield Tick()
  print( "CSR Tests: %d Passed, %d Failed"%( p, f ) )

# 'main' method to run a basic testbench.
if __name__ == "__main__":
  # Instantiate a CSR module.
  dut = CSR()
  # Run the tests.
  with Simulator( dut, vcd_file = open( 'csr.vcd', 'w' ) ) as sim:
    def proc():
      yield from csr_test( dut )
    sim.add_clock( 1e-6 )
    sim.add_sync_process( proc )
    sim.run()
