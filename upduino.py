from nmigen.build import *
from nmigen.vendor.lattice_ice40 import *
from nmigen_boards.resources import *

import os
import subprocess

__all__ = ["PINS", "UpduinoPlatform"]

PINS = [ 2, 3, 4, 9, 11, 13, 18, 19, 21, 23, 25, 26, 27, 31, 32,
         34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48 ]

class UpduinoPlatform(LatticeICE40Platform):
    device      = "iCE40UP5K"
    package     = "SG48"
    default_clk = "SB_HFOSC"
    hfosc_div   = 3
    resources   = [
        *LEDResources(pins="39 40 41", invert=True,
                      attrs=Attrs(IO_STANDARD="SB_LVCMOS")),
        *SPIFlashResources(0,
            cs="16", clk="15", miso="17", mosi="14",
            attrs=Attrs(IO_STANDARD="SB_LVCMOS")
        ),
        # Solder pin 12 to the adjacent 'J8' osc_out pin to enable.
        Resource("clk12", 0, Pins("12", dir="i"),
                 Clock(12e6), Attrs(IO_STANDARD="SB_LVCMOS")),
    ]

    for i in PINS:
      resources.append(Resource("gpio", i, Pins("%d"%i, dir="io"),
               Attrs(IO_STANDARD = "SB_LVCMOS")))
    connectors  = [
        # "Left" row of header pins (JP5 on the schematic)
        Connector("j", 0, "- - 23 25 26 27 32 35 31 37 34 43 36 42 38 28"),
        # "Right" row of header pins (JP6 on the schematic)
        Connector("j", 1, "12 21 13 19 18 11 9 6 44 4 3 48 45 47 46 2")
    ]

    def toolchain_program(self, products, name):
        iceprog = os.environ.get("ICEPROG", "iceprog")
        with products.extract("{}.bin".format(name)) as bitstream_filename:
            subprocess.check_call([iceprog, bitstream_filename])

if __name__ == "__main__":
    from nmigen_boards.test.blinky import *
    UpduinoPlatform().build(Blinky(), do_program=True)
