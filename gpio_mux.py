from nmigen import *
from nmigen.lib.io import *
from nmigen.back.pysim import *
from nmigen_soc.wishbone import *
from nmigen_soc.memory import *

from isa import *
from upduino import *

##########################################
# GPIO multiplexer interface:            #
# Map I/O pins to different peripherals. #
# Each pin gets 4 bits:                  #
# * 0x0: GPIO (default)                  #
# * 0xN: PWM peripheral #(N)             #
##########################################

# Number of PWM peripherals to expect.
PWM_PERIPHS = 3

# Dummy GPIO pin class for simulations.
class DummyGPIO():
  def __init__( self, name ):
    self.o  = Signal( name = "%s_o"%name )
    self.i  = Signal( name = "%s_i"%name )
    self.oe = Signal( name = "%s_oe"%name )

class GPIO_Mux( Elaboratable, Interface ):
  def __init__( self, periphs ):
    # Wishbone interface: address <=64 pins, 4 bits per pin.
    # The bus is 32 bits wide for compatibility, so 8 pins per word.
    Interface.__init__( self, addr_width = 6, data_width = 32 )
    self.memory_map = MemoryMap( addr_width = self.addr_width,
                                 data_width = self.data_width,
                                 alignment = 0 )

    # Backing data store for QFN48 pins. A 'Memory' would be more
    # efficient, but the module must access each field in parallel.
    self.pin_mux = Array(
      Signal( 4, reset = 0, name = "pin_func_%d"%i ) if i in PINS else None
      for i in range( 49 ) )

    # Unpack peripheral modules (passed in from 'rvmem.py' module).
    self.gpio = periphs[ 0 ]
    self.pwm = []
    pind = 1
    for i in range( PWM_PERIPHS ):
      self.pwm.append( periphs[ pind ] )
      pind += 1

  def elaborate( self, platform ):
    m = Module()

    # Set up I/O pin resources.
    if platform is None:
      self.p = Array(
        DummyGPIO( "pin_%d"%i ) if i in PINS else None
        for i in range( max( PINS ) + 1 ) )
    else:
      self.p = Array(
        platform.request( "gpio", i ) if i in PINS else None
        for i in range( max( PINS ) + 1 ) )

    # Read bits default to 0. Bus signals follow 'cyc'.
    m.d.comb += [
      self.dat_r.eq( 0 ),
      self.stb.eq( self.cyc ),
    ]
    m.d.sync +=  self.ack.eq( self.cyc )

    # Switch case to read/write the currently-addressed register.
    # This peripheral must be accessed with a word-aligned address.
    with m.Switch( self.adr ):
      # 49 pin addresses (0-48), 8 pins per register, so 7 registers.
      for i in range( 7 ):
        with m.Case( i * 4 ):
          # Read logic for valid pins (each has 4 bits).
          for j in range( 8 ):
            pnum = ( i * 8 ) + j
            if pnum in PINS:
              m.d.comb += self.dat_r.bit_select( j * 4, 4 ).eq(
                self.pin_mux[ pnum ] )
              # Write logic for valid pins (again, 4 bits each).
              with m.If( ( self.cyc == 1 ) &
                         ( self.we == 1 ) ):
                m.d.sync += self.pin_mux[ pnum ].eq(
                  self.dat_w.bit_select( j * 4, 4 ) )

    # Pin multiplexing logic.
    for i in range( 49 ):
      if i in PINS:
        # Each valid pin gets its own switch case, which ferries
        # signals between the selected peripheral and the actual pin.
        with m.Switch( self.pin_mux[ i ] ):
          pind = 1
          # GPIO peripheral:
          with m.Case( 0 ):
            # Apply 'value' and 'direction' bits.
            m.d.sync += self.p[ i ].oe.eq( self.gpio.p[ i ][ 1 ] )
            # Read or write, depending on the 'direction' bit.
            with m.If( self.gpio.p[ i ][ 1 ] == 0 ):
              m.d.sync += self.gpio.p[ i ].bit_select( 0, 1 ) \
                .eq( self.p[ i ].i )
            with m.Else():
              m.d.sync += self.p[ i ].o.eq( self.gpio.p[ i ][ 0 ] )
          # PWM peripherals:
          for j in range( PWM_PERIPHS ):
            with m.Case( pind ):
              # Set pin to output mode, and set its current value.
              m.d.sync += [
                self.p[ i ].oe.eq( 1 ),
                self.p[ i ].o.eq( self.pwm[ j ].o )
              ]
            pind += 1

    # (End of GPIO multiplexer module)
    return m
