from nmigen import *
from nmigen.lib.io import *
from nmigen.back.pysim import *
from nmigen_soc.wishbone import *
from nmigen_soc.memory import *

from isa import *
from upduino import *

##################################
# GPIO interface: allow I/O pins #
# to be written and read.        #
##################################

class GPIO( Elaboratable, Interface ):
  def __init__( self ):
    # Initialize wishbone bus interface to support up to 64 pins.
    # Each pin has two bits, so there are 16 pins per register:
    # * 0: value. Contains the current I/O pin value. Only writable
    #      in output mode. Writes to input pins are ignored.
    #      (But they might get applied when the direction switches?)
    # * 1: direction. When set to '0', the pin is in input mode and
    #      its output is disabled. When set to '1', it is in output
    #      mode and the value in bit 0 will be reflected on the pin.
    #
    # iCE40s don't have programmable pulling resistors, so...
    # not many options here. You get an I, and you get an O.
    Interface.__init__( self, addr_width = 5, data_width = 32 )
    self.memory_map = MemoryMap( addr_width = self.addr_width,
                                 data_width = self.data_width,
                                 alignment = 0 )
    # Backing data store. A 'Memory' would be smaller, but
    # the 'pin multiplexer' peripheral needs parallel access.
    self.p = Array(
      Signal( 2, reset = 0, name = "gpio_%d"%i ) if i in PINS else None
      for i in range( 49 ) )

  def elaborate( self, platform ):
    m = Module()

    # Read bits default to 0. Bus signals follow 'cyc'.
    m.d.comb += [
      self.dat_r.eq( 0 ),
      self.stb.eq( self.cyc )
    ]
    m.d.sync += self.ack.eq( self.cyc )

    # Switch case to select the currently-addressed register.
    # This peripheral must be accessed with a word-aligned address.
    with m.Switch( self.adr ):
      for i in range( 4 ):
        with m.Case( i * 4 ):
          # Logic for each of the register's 16 possible pins,
          # ignoring ones that aren't in the 'PINS' array.
          for j in range( 16 ):
            pnum = ( i * 16 ) + j
            if pnum in PINS:
              # Read logic: populate 'value' and 'direction' bits.
              m.d.comb += self.dat_r.bit_select( j * 2, 2 ).eq(
                self.p[ pnum ] )
              # Write logic: if this bus is selected and writes
              # are enabled, set 'value' and 'direction' bits.
              with m.If( ( self.we == 1 ) & ( self.cyc == 1 ) ):
                m.d.sync += self.p[ pnum ].eq(
                  self.dat_w.bit_select( j * 2, 2 ) )

    # (End of GPIO peripheral module definition)
    return m
