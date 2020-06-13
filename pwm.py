from nmigen import *
from nmigen_soc.wishbone import *
from nmigen_soc.memory import *

################################################
# PWM "Pulse Width Modulation" peripheral      #
# Produces a PWM output based on an 8-bit      #
# value that constantly counts up.             #
# When the counter is less than the 'compare'  #
# value, the output is 1. When it reaches the  #
# max value of 0xFF, it resets. If 'compare'   #
# is 0, the output is effectively disabled.    #
################################################

# Peripheral register offset (there's only one, so...zero)
# Bits 0-8:  'compare' value.
PWM_CR = 0

class PWM( Elaboratable, Interface ):
  def __init__( self ):
    # Initialize wishbone bus interface for peripheral registers.
    # This seems sort of pointless with only one register, but
    # it lets the peripheral be added to the wider memory map.
    Interface.__init__( self, addr_width = 1, data_width = 32 )
    self.memory_map = MemoryMap( addr_width = self.addr_width,
                                 data_width = self.data_width,
                                 alignment = 0 )
    # Peripheral signals. Use 8 bits to allow duty cycles
    # to be set with a granularity of ~0.4%
    self.compare = Signal( 8, reset = 0 )
    self.count   = Signal( 8, reset = 0 )
    # Current output value.
    self.o       = Signal( 1,  reset = 0 )

  def elaborate( self, platform ):
    m = Module()

    m.d.comb += [
      # Set the pin output value.
      # TODO: This is backwards, because the LEDs are wired backwards
      # on most iCE40 boards. It should be '<', not '>='.
      self.o.eq( self.count >= self.compare ),
      # Peripheral bus signals follow 'cyc'.
      self.stb.eq( self.cyc )
    ]
    m.d.sync += [
      # Increment the counter.
      self.count.eq( self.count + 1 ),
      # Peripheral bus signals follow 'cyc'.
      self.ack.eq( self.cyc )
    ]

    # There's only one peripheral register, so we don't really need
    # a switch case. Only address 0 is valid.
    with m.If( self.adr == 0 ):
      # The "compare" value is located in the register's 8 LSbits.
      m.d.comb += self.dat_r.eq( self.compare )
      with m.If( self.we & self.cyc ):
        m.d.sync += self.compare.eq( self.dat_w[ :8 ] )

    return m
