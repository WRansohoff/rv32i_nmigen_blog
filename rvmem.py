from nmigen import *
from nmigen.back.pysim import *
from nmigen_soc.wishbone import *
from nmigen_soc.memory import *

from gpio import *
from gpio_mux import *
from pwm import *
from ram import *

#############################################################
# "RISC-V Memories" module.                                 #
# This directs memory accesses to the appropriate submodule #
# based on the memory space defined by the 3 MSbits.        #
# (None of this is actually part of the RISC-V spec)        #
# Current memory spaces:                                    #
# *  0x0------- = ROM                                       #
# *  0x2------- = RAM                                       #
# *  0x4------- = Peripherals                               #
# ** 0x4000---- = GPIO pins                                 #
# ** 0x4001---- = GPIO multiplexer                          #
# ** 0x4002---- = PWM peripherals                           #
# ** 0x40020x-- = PWM peripheral #(x-1)                     #
#############################################################

class RV_Memory( Elaboratable ):
  def __init__( self, rom_module, ram_words ):
    # Memory multiplexers.
    # Data bus multiplexer.
    self.dmux = Decoder( addr_width = 32,
                         data_width = 32,
                         alignment = 0 )
    # Instruction bus multiplexer.
    self.imux = Decoder( addr_width = 32,
                         data_width = 32,
                         alignment = 0 )

    # Add ROM and RAM buses to the data multiplexer.
    self.rom = rom_module
    self.ram = RAM( ram_words )
    self.rom_d = self.rom.new_bus()
    self.ram_d = self.ram.new_bus()
    self.dmux.add( self.rom_d,    addr = 0x00000000 )
    self.dmux.add( self.ram_d,    addr = 0x20000000 )
    # Add peripheral buses to the data multiplexer.
    self.gpio = GPIO()
    self.dmux.add( self.gpio,     addr = 0x40000000 )
    self.pwm = []
    p_adr = 0x40020000
    for i in range( PWM_PERIPHS ):
      self.pwm.append( PWM() )
      self.dmux.add( self.pwm[ i ], addr = p_adr )
      p_adr += 0x0100
    gpio_mux_arr = [ self.gpio ]
    gpio_mux_arr.extend( self.pwm )
    self.gpio_mux = GPIO_Mux( gpio_mux_arr )
    self.dmux.add( self.gpio_mux, addr = 0x40010000 )

    # Add ROM and RAM buses to the instruction multiplexer.
    self.rom_i = self.rom.new_bus()
    self.ram_i = self.ram.new_bus()
    self.imux.add( self.rom_i,    addr = 0x00000000 )
    self.imux.add( self.ram_i,    addr = 0x20000000 )
    # (No peripherals on the instruction bus)

  def elaborate( self, platform ):
    m = Module()
    # Register the multiplexers, peripherals, and memory submodules.
    m.submodules.dmux     = self.dmux
    m.submodules.imux     = self.imux
    m.submodules.rom      = self.rom
    m.submodules.ram      = self.ram
    m.submodules.gpio     = self.gpio
    for i in range( PWM_PERIPHS ):
      setattr( m.submodules, "pwm%i"%i, self.pwm[ i ] )
    m.submodules.gpio_mux = self.gpio_mux

    # Currently, all bus cycles are single-transaction.
    # So set the 'strobe' signals equal to the 'cycle' ones.
    m.d.comb += [
      self.dmux.bus.stb.eq( self.dmux.bus.cyc ),
      self.imux.bus.stb.eq( self.imux.bus.cyc )
    ]

    return m
