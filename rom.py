from nmigen import *
from math import ceil, log2
from nmigen.back.pysim import *
from nmigen_soc.memory import *
from nmigen_soc.wishbone import *

from isa import *

###############
# ROM module: #
###############

class ROM( Elaboratable ):
  def __init__( self, data ):
    # Data storage.
    self.data = Memory( width = 32, depth = len( data ), init = data )
    # Memory read port.
    self.r = self.data.read_port()
    # Record size.
    self.size = len( data ) * 4
    # Initialize Wishbone bus arbiter.
    self.arb = Arbiter( addr_width = ceil( log2( self.size + 1 ) ),
                        data_width = 32 )
    self.arb.bus.memory_map = MemoryMap(
      addr_width = self.arb.bus.addr_width,
      data_width = self.arb.bus.data_width,
      alignment = 0 )

  def new_bus( self ):
    # Initialize a new Wishbone bus interface.
    bus = Interface( addr_width = self.arb.bus.addr_width,
                     data_width = self.arb.bus.data_width )
    bus.memory_map = MemoryMap( addr_width = bus.addr_width,
                                data_width = bus.data_width,
                                alignment = 0 )
    self.arb.add( bus )
    return bus

  def elaborate( self, platform ):
    m = Module()
    m.submodules.arb = self.arb
    m.submodules.r = self.r

    # Ack two cycles after activation, for memory port access and
    # synchronous read-out (to prevent combinatorial loops).
    rws = Signal( 1, reset = 0 )
    m.d.sync += [
      rws.eq( self.arb.bus.cyc ),
      self.arb.bus.ack.eq( self.arb.bus.cyc & rws )
    ]

    # Set read port address (in words).
    m.d.comb += self.r.addr.eq( self.arb.bus.adr >> 2 )
    # Set the 'output' value to the requested 'data' array index.
    # If a read would 'spill over' into an out-of-bounds data byte,
    # set that byte to 0x00.
    # Word-aligned reads
    with m.If( ( self.arb.bus.adr & 0b11 ) == 0b00 ):
      m.d.sync += self.arb.bus.dat_r.eq( LITTLE_END_L( self.r.data ) )
    # Un-aligned reads
    with m.Else():
      m.d.sync += self.arb.bus.dat_r.eq(
        LITTLE_END_L( self.r.data << ( ( self.arb.bus.adr & 0b11 ) << 3 ) ) )
    # End of ROM module definition.
    return m

##################
# ROM testbench: #
##################
# Keep track of test pass / fail rates.
p = 0
f = 0

# Perform an individual ROM unit test.
def rom_read_ut( rom, address, expected ):
  global p, f
  # Set address, and wait two ticks.
  yield rom.arb.bus.adr.eq( address )
  yield Tick()
  yield Tick()
  # Done. Check the result after combinational logic settles.
  yield Settle()
  actual = yield rom.arb.bus.dat_r
  if expected != actual:
    f += 1
    print( "\033[31mFAIL:\033[0m ROM[ 0x%08X ] = 0x%08X (got: 0x%08X)"
           %( address, expected, actual ) )
  else:
    p += 1
    print( "\033[32mPASS:\033[0m ROM[ 0x%08X ] = 0x%08X"
           %( address, expected ) )

# Top-level ROM test method.
def rom_test( rom ):
  global p, f

  # Let signals settle after reset.
  yield Settle()
  # Print a test header.
  print( "--- ROM Tests ---" )
  # Assert 'cyc' to activate the bus.
  yield rom.arb.bus.cyc.eq( 1 )
  # Test the ROM's "happy path" (reading valid data).

  yield from rom_read_ut( rom, 0x0, LITTLE_END( 0x01234567 ) )
  yield from rom_read_ut( rom, 0x4, LITTLE_END( 0x89ABCDEF ) )
  yield from rom_read_ut( rom, 0x8, LITTLE_END( 0x42424242 ) )
  yield from rom_read_ut( rom, 0xC, LITTLE_END( 0xDEADBEEF ) )
  # Test byte-aligned and halfword-aligned addresses.
  yield from rom_read_ut( rom, 0x1, LITTLE_END( 0x23456700 ) )
  yield from rom_read_ut( rom, 0x2, LITTLE_END( 0x45670000 ) )
  yield from rom_read_ut( rom, 0x3, LITTLE_END( 0x67000000 ) )
  yield from rom_read_ut( rom, 0x5, LITTLE_END( 0xABCDEF00 ) )
  yield from rom_read_ut( rom, 0x6, LITTLE_END( 0xCDEF0000 ) )
  yield from rom_read_ut( rom, 0x7, LITTLE_END( 0xEF000000 ) )
  # Test reading the last few bytes of data.
  yield from rom_read_ut( rom, rom.size - 4, LITTLE_END( 0xDEADBEEF ) )
  yield from rom_read_ut( rom, rom.size - 3, LITTLE_END( 0xADBEEF00 ) )
  yield from rom_read_ut( rom, rom.size - 2, LITTLE_END( 0xBEEF0000 ) )
  yield from rom_read_ut( rom, rom.size - 1, LITTLE_END( 0xEF000000 ) )

  # Done.
  yield Tick()
  print( "ROM Tests: %d Passed, %d Failed"%( p, f ) )

# 'main' method to run a basic testbench.
if __name__ == "__main__":
  # Instantiate a test ROM module with 16 bytes of data.
  dut = ROM( [ 0x01234567, 0x89ABCDEF, 0x42424242, 0xDEADBEEF ] )
  # Run the ROM tests.
  with Simulator( dut, vcd_file = open( 'rom.vcd', 'w' ) ) as sim:
    def proc():
      yield from rom_test( dut )
    sim.add_clock( 1e-6 )
    sim.add_sync_process( proc )
    sim.run()
