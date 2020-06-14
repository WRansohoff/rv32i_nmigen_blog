from nmigen import *
from nmigen.back.pysim import *

from alu import *
from csr import *
from isa import *
from spi_rom import *
from rom import *
from rvmem import *

import os
import sys
import warnings

# Optional: Enable verbose output for debugging.
#os.environ["NMIGEN_verbose"] = "Yes"

# CPU module.
class CPU( Elaboratable ):
  def __init__( self, rom_module ):
    # CPU signals:
    # 'Reset' signal for clock domains.
    self.clk_rst = Signal( reset = 0b0, reset_less = True )
    # Program Counter register.
    self.pc = Signal( 32, reset = 0x00000000 )
    # The main 32 CPU registers.
    self.r      = Memory( width = 32, depth = 32,
                          init = ( 0x00000000 for i in range( 32 ) ) )

    # CPU submodules:
    # Memory access ports for rs1 (ra), rs2 (rb), and rd (rc).
    self.ra     = self.r.read_port()
    self.rb     = self.r.read_port()
    self.rc     = self.r.write_port()
    # The ALU submodule which performs logical operations.
    self.alu    = ALU()
    # CSR 'system registers'.
    self.csr    = CSR()
    # Memory module to hold peripherals and ROM / RAM module(s)
    # (4KB of RAM = 1024 words)
    self.mem    = RV_Memory( rom_module, 1024 )

  # Helper method to enter a trap handler: jump to the appropriate
  # address, and set the MCAUSE / MEPC CSRs.
  def trigger_trap( self, m, trap_num, return_pc ):
    m.d.sync += [
      # Set mcause, mepc, interrupt context flag.
      self.csr.mcause_interrupt.eq( 0 ),
      self.csr.mcause_ecode.eq( trap_num ),
      self.csr.mepc_mepc.eq( return_pc.bit_select( 2, 30 ) ),
      # Disable interrupts globally until MRET or CSR write.
      self.csr.mstatus_mie.eq( 0 ),
      # Set the program counter to the interrupt handler address.
      self.pc.eq( Cat( Repl( 0, 2 ),
                     ( self.csr.mtvec_base +
                       Mux( self.csr.mtvec_mode, trap_num, 0 ) ) ) )
    ]

  # CPU object's 'elaborate' method to generate the hardware logic.
  def elaborate( self, platform ):
    # Core CPU module.
    m = Module()
    # Register the ALU, CSR, and memory submodules.
    m.submodules.alu = self.alu
    m.submodules.csr = self.csr
    m.submodules.mem = self.mem
    # Register the CPU register read/write ports.
    m.submodules.ra  = self.ra
    m.submodules.rb  = self.rb
    m.submodules.rc  = self.rc

    # Wait-state counter to let internal memories load.
    iws = Signal( 2, reset = 0 )

    # Top-level combinatorial logic.
    m.d.comb += [
      # Set CPU register access addresses.
      self.ra.addr.eq( self.mem.imux.bus.dat_r[ 15 : 20 ] ),
      self.rb.addr.eq( self.mem.imux.bus.dat_r[ 20 : 25 ] ),
      self.rc.addr.eq( self.mem.imux.bus.dat_r[ 7  : 12 ] ),
      # Instruction bus address is always set to the program counter.
      self.mem.imux.bus.adr.eq( self.pc ),
      # The CSR inputs are always wired the same.
      self.csr.dat_w.eq(
        Mux( self.mem.imux.bus.dat_r[ 14 ] == 0,
             self.ra.data,
             Cat( self.ra.addr,
                  Repl( self.ra.addr[ 4 ], 27 ) ) ) ),
      self.csr.f.eq( self.mem.imux.bus.dat_r[ 12 : 15 ] ),
      self.csr.adr.eq( self.mem.imux.bus.dat_r[ 20 : 32 ] ),
      # Store data and width are always wired the same.
      self.mem.ram.dw.eq( self.mem.imux.bus.dat_r[ 12 : 15 ] ),
      self.mem.dmux.bus.dat_w.eq( self.rb.data ),
    ]

    # Trigger an 'instruction mis-aligned' trap if necessary. 
    with m.If( self.pc[ :2 ] != 0 ):
      m.d.sync += self.csr.mtval_einfo.eq( self.pc )
      self.trigger_trap( m, TRAP_IMIS, Past( self.pc ) )
    with m.Else():
      # I-bus is active until it completes a transaction.
      m.d.comb += self.mem.imux.bus.cyc.eq( iws == 0 )

    # Wait a cycle after 'ack' to load the appropriate CPU registers.
    with m.If( self.mem.imux.bus.ack ):
      # Increment the wait-state counter.
      # (This also lets the instruction bus' 'cyc' signal fall.)
      m.d.sync += iws.eq( 1 )
      with m.If( iws == 0 ):
        # Increment pared-down 32-bit MINSTRET counter.
        # I'd remove the whole MINSTRET CSR to save space, but the
        # test harnesses depend on it to count instructions.
        # TODO: This is OBO; it'll be 1 before the first retire.
        m.d.sync += self.csr.minstret_instrs.eq(
          self.csr.minstret_instrs + 1 )

    # Execute the current instruction, once it loads.
    with m.If( iws != 0 ):
      # Increment the PC and reset the wait-state unless
      # otherwise specified.
      m.d.sync += [
        self.pc.eq( self.pc + 4 ),
        iws.eq( 0 )
      ]

      # Decoder switch case:
      with m.Switch( self.mem.imux.bus.dat_r[ 0 : 7 ] ):
        # LUI / AUIPC / R-type / I-type instructions: apply
        # pending CPU register write.
        with m.Case( '0-10-11' ):
          m.d.comb += self.rc.en.eq( self.rc.addr != 0 )

        # JAL / JALR instructions: jump to a new address and place
        # the 'return PC' in the destination register (rc).
        with m.Case( '110-111' ):
          m.d.sync += self.pc.eq(
            Mux( self.mem.imux.bus.dat_r[ 3 ],
                 self.pc + Cat(
                   Repl( 0, 1 ),
                   self.mem.imux.bus.dat_r[ 21: 31 ],
                   self.mem.imux.bus.dat_r[ 20 ],
                   self.mem.imux.bus.dat_r[ 12 : 20 ],
                   Repl( self.mem.imux.bus.dat_r[ 31 ], 12 ) ),
                 self.ra.data + Cat(
                   self.mem.imux.bus.dat_r[ 20 : 32 ],
                   Repl( self.mem.imux.bus.dat_r[ 31 ], 20 ) ) ),
          )
          m.d.comb += self.rc.en.eq( self.rc.addr != 0 )

        # Conditional branch instructions: similar to JAL / JALR,
        # but only take the branch if the condition is met.
        with m.Case( OP_BRANCH ):
          # Check the ALU result. If it is zero, then:
          # a == b for BEQ/BNE, or a >= b for BLT[U]/BGE[U].
          with m.If( ( ( self.alu.y == 0 ) ^
                         self.mem.imux.bus.dat_r[ 12 ] ) !=
                       self.mem.imux.bus.dat_r[ 14 ] ):
            # Branch only if the condition is met.
            m.d.sync += self.pc.eq( self.pc + Cat(
              Repl( 0, 1 ),
              self.mem.imux.bus.dat_r[ 8 : 12 ],
              self.mem.imux.bus.dat_r[ 25 : 31 ],
              self.mem.imux.bus.dat_r[ 7 ],
              Repl( self.mem.imux.bus.dat_r[ 31 ], 20 ) ) )

        # Load / Store instructions: perform memory access
        # through the data bus.
        with m.Case( '0-00011' ):
          # Trigger a trap if the address is mis-aligned.
          # * Byte accesses are never mis-aligned.
          # * Word-aligned accesses are never mis-aligned.
          # * Halfword accesses are only mis-aligned when both of
          #   the address' LSbits are 1s.
          with m.If( ( ( self.mem.dmux.bus.adr[ :2 ] == 0 ) |
                       ( self.mem.imux.bus.dat_r[ 12 : 14 ] == 0 ) |
                       ( ~( self.mem.dmux.bus.adr[ 0 ] &
                            self.mem.dmux.bus.adr[ 1 ] &
                            self.mem.imux.bus.dat_r[ 12 ] ) ) ) == 0 ):
            self.trigger_trap( m,
              Cat( Repl( 0, 1 ),
                   self.mem.imux.bus.dat_r[ 5 ],
                   Repl( 1, 1 ) ),
              Past( self.pc ) )
          with m.Else():
            # Activate the data bus.
            m.d.comb += [
              self.mem.dmux.bus.cyc.eq( 1 ),
              # Stores only: set the 'write enable' bit.
              self.mem.dmux.bus.we.eq( self.mem.imux.bus.dat_r[ 5 ] )
            ]
            # Don't proceed until the memory access finishes.
            with m.If( self.mem.dmux.bus.ack == 0 ):
              m.d.sync += [
                self.pc.eq( self.pc ),
                iws.eq( 2 )
              ]
            # Loads only: write to the CPU register.
            with m.Elif( self.mem.imux.bus.dat_r[ 5 ] == 0 ):
              m.d.comb += self.rc.en.eq( self.rc.addr != 0 )

        # System call instruction: ECALL, EBREAK, MRET,
        # and atomic CSR operations.
        with m.Case( OP_SYSTEM ):
          with m.If( self.mem.imux.bus.dat_r[ 12 : 15 ] == F_TRAPS ):
            with m.Switch( self.mem.imux.bus.dat_r[ 20 : 22 ] ):
              # An 'empty' ECALL instruction should raise an
              # 'environment-call-from-M-mode" exception.
              with m.Case( 0 ):
                self.trigger_trap( m, TRAP_ECALL, Past( self.pc ) )
              # "EBREAK" instruction: enter the interrupt context
              # with 'breakpoint' as the cause of the exception.
              with m.Case( 1 ):
                self.trigger_trap( m, TRAP_BREAK, Past( self.pc ) )
              # 'MRET' jumps to the stored 'pre-trap' PC in the
              # 30 MSbits of the MEPC CSR.
              with m.Case( 2 ):
                m.d.sync += [
                  self.csr.mstatus_mie.eq( 1 ),
                  self.pc.eq( Cat( Repl( 0, 2 ),
                                   self.csr.mepc_mepc ) )
                ]
          # Defer to the CSR module for atomic CSR reads/writes.
          # 'CSRR[WSC]': Write/Set/Clear CSR value from a register.
          # 'CSRR[WSC]I': Write/Set/Clear CSR value from immediate.
          with m.Else():
            m.d.comb += [
              self.rc.data.eq( self.csr.dat_r ),
              self.rc.en.eq( self.rc.addr != 0 ),
              self.csr.we.eq( 1 )
            ]

        # FENCE instruction: clear any I-caches and ensure all
        # memory operations are applied. There is no I-cache,
        # and there is no caching of memory operations.
        # There is also no pipelining. So...this is a nop.
        with m.Case( OP_FENCE ):
          pass

    # 'Always-on' decode/execute logic:
    with m.Switch( self.mem.imux.bus.dat_r[ 0 : 7 ] ):
      # LUI / AUIPC instructions: set destination register to
      # 20 upper bits, +pc for AUIPC.
      with m.Case( '0-10111' ):
        m.d.comb += self.rc.data.eq(
          Mux( self.mem.imux.bus.dat_r[ 5 ], 0, self.pc ) +
          Cat( Repl( 0, 12 ),
               self.mem.imux.bus.dat_r[ 12 : 32 ] ) )

      # JAL / JALR instructions: set destination register to
      # the 'return PC' value.
      with m.Case( '110-111' ):
        m.d.comb += self.rc.data.eq( self.pc + 4 )

      # Conditional branch instructions:
      # set us up the ALU for the condition check.
      with m.Case( OP_BRANCH ):
        # BEQ / BNE: use SUB ALU operation to check equality.
        # BLT / BGE / BLTU / BGEU: use SLT or SLTU ALU operation.
        m.d.comb += [
          self.alu.a.eq( self.ra.data ),
          self.alu.b.eq( self.rb.data ),
          self.alu.f.eq( Mux(
            self.mem.imux.bus.dat_r[ 14 ],
            Cat( self.mem.imux.bus.dat_r[ 13 ], 0b001 ),
            0b1000 ) )
        ]

      # Load instructions: Set the memory address and data register.
      with m.Case( OP_LOAD ):
        m.d.comb += [
          self.mem.dmux.bus.adr.eq( self.ra.data +
            Cat( self.mem.imux.bus.dat_r[ 20 : 32 ],
                 Repl( self.mem.imux.bus.dat_r[ 31 ], 20 ) ) ),
          self.rc.data.bit_select( 0, 8 ).eq(
            self.mem.dmux.bus.dat_r[ :8 ] )
        ]
        with m.If( self.mem.imux.bus.dat_r[ 12 ] ):
          m.d.comb += [
            self.rc.data.bit_select( 8, 8 ).eq(
              self.mem.dmux.bus.dat_r[ 8 : 16 ] ),
            self.rc.data.bit_select( 16, 16 ).eq(
              Repl( ( self.mem.imux.bus.dat_r[ 14 ] == 0 ) &
                    self.mem.dmux.bus.dat_r[ 15 ], 16 ) )
          ]
        with m.Elif( self.mem.imux.bus.dat_r[ 13 ] ):
          m.d.comb += self.rc.data.bit_select( 8, 24 ).eq(
            self.mem.dmux.bus.dat_r[ 8 : 32 ] )
        with m.Else():
          m.d.comb += self.rc.data.bit_select( 8, 24 ).eq(
            Repl( ( self.mem.imux.bus.dat_r[ 14 ] == 0 ) &
                  self.mem.dmux.bus.dat_r[ 7 ], 24 ) )

      # Store instructions: Set the memory address.
      with m.Case( OP_STORE ):
        m.d.comb += self.mem.dmux.bus.adr.eq( self.ra.data +
          Cat( self.mem.imux.bus.dat_r[ 7 : 12 ],
               self.mem.imux.bus.dat_r[ 25 : 32 ],
               Repl( self.mem.imux.bus.dat_r[ 31 ], 20 ) ) )

      # R-type ALU operation: set inputs for rc = ra ? rb
      with m.Case( OP_REG ):
        # Implement left shifts using the right shift ALU operation.
        with m.If( self.mem.imux.bus.dat_r[ 12 : 15 ] == 0b001 ):
          m.d.comb += [
            self.alu.a.eq( FLIP( self.ra.data ) ),
            self.alu.f.eq( 0b0101 ),
            self.rc.data.eq( FLIP( self.alu.y ) )
          ]
        with m.Else():
          m.d.comb += [
            self.alu.a.eq( self.ra.data ),
            self.alu.f.eq( Cat(
              self.mem.imux.bus.dat_r[ 12 : 15 ],
              self.mem.imux.bus.dat_r[ 30 ] ) ),
            self.rc.data.eq( self.alu.y ),
          ]
        m.d.comb += self.alu.b.eq( self.rb.data )

      # I-type ALU operation: set inputs for rc = ra ? immediate
      with m.Case( OP_IMM ):
        # Shift operations are a bit different from normal I-types.
        # They use 'funct7' bits like R-type operations, and the
        # left shift can be implemented as a right shift to avoid
        # having two barrel shifters in the ALU.
        with m.If( self.mem.imux.bus.dat_r[ 12 : 14 ] == 0b01 ):
          with m.If( self.mem.imux.bus.dat_r[ 14 ] == 0 ):
            m.d.comb += [
              self.alu.a.eq( FLIP( self.ra.data ) ),
              self.alu.f.eq( 0b0101 ),
              self.rc.data.eq( FLIP( self.alu.y ) ),
            ]
          with m.Else():
            m.d.comb += [
              self.alu.a.eq( self.ra.data ),
              self.alu.f.eq( Cat( 0b101, self.mem.imux.bus.dat_r[ 30 ] ) ),
              self.rc.data.eq( self.alu.y ),
            ]
        # Normal I-type operation:
        with m.Else():
          m.d.comb += [
            self.alu.a.eq( self.ra.data ),
            self.alu.f.eq( self.mem.imux.bus.dat_r[ 12 : 15 ] ),
            self.rc.data.eq( self.alu.y ),
          ]
        # Shared I-type logic:
        m.d.comb += self.alu.b.eq( Cat(
          self.mem.imux.bus.dat_r[ 20 : 32 ],
          Repl( self.mem.imux.bus.dat_r[ 31 ], 20 ) ) )

    # End of CPU module definition.
    return m

##################
# CPU testbench: #
##################
# Keep track of test pass / fail rates.
p = 0
f = 0

# Import test programs and expected runtime register values.
from programs import *

# Helper method to check expected CPU register / memory values
# at a specific point during a test program.
def check_vals( expected, ni, cpu ):
  global p, f
  if ni in expected:
    for j in range( len( expected[ ni ] ) ):
      ex = expected[ ni ][ j ]
      # Special case: program counter.
      if ex[ 'r' ] == 'pc':
        cpc = yield cpu.pc
        if hexs( cpc ) == hexs( ex[ 'e' ] ):
          p += 1
          print( "  \033[32mPASS:\033[0m pc  == %s"
                 " after %d operations"
                 %( hexs( ex[ 'e' ] ), ni ) )
        else:
          f += 1
          print( "  \033[31mFAIL:\033[0m pc  == %s"
                 " after %d operations (got: %s)"
                 %( hexs( ex[ 'e' ] ), ni, hexs( cpc ) ) )
      # Special case: RAM data (must be word-aligned).
      elif type( ex[ 'r' ] ) == str and ex[ 'r' ][ 0:3 ] == "RAM":
        rama = int( ex[ 'r' ][ 3: ] )
        if ( rama % 4 ) != 0:
          f += 1
          print( "  \033[31mFAIL:\033[0m RAM == %s @ 0x%08X"
                 " after %d operations (mis-aligned address)"
                 %( hexs( ex[ 'e' ] ), rama, ni ) )
        else:
          cpd = yield cpu.mem.ram.data[ rama // 4 ]
          if hexs( cpd ) == hexs( ex[ 'e' ] ):
            p += 1
            print( "  \033[32mPASS:\033[0m RAM == %s @ 0x%08X"
                   " after %d operations"
                   %( hexs( ex[ 'e' ] ), rama, ni ) )
          else:
            f += 1
            print( "  \033[31mFAIL:\033[0m RAM == %s @ 0x%08X"
                   " after %d operations (got: %s)"
                   %( hexs( ex[ 'e' ] ), rama, ni, hexs( cpd ) ) )
      # Numbered general-purpose registers.
      elif ex[ 'r' ] >= 0 and ex[ 'r' ] < 32:
        cr = yield cpu.r[ ex[ 'r' ] ]
        if hexs( cr ) == hexs( ex[ 'e' ] ):
          p += 1
          print( "  \033[32mPASS:\033[0m r%02d == %s"
                 " after %d operations"
                 %( ex[ 'r' ], hexs( ex[ 'e' ] ), ni ) )
        else:
          f += 1
          print( "  \033[31mFAIL:\033[0m r%02d == %s"
                 " after %d operations (got: %s)"
                 %( ex[ 'r' ], hexs( ex[ 'e' ] ),
                    ni, hexs( cr ) ) )

# Helper method to run a CPU device for a given number of cycles,
# and verify its expected register values over time.
def cpu_run( cpu, expected ):
  global p, f
  # Record how many CPU instructions have been executed.
  ni = -1
  # Watch for timeouts if the CPU gets into a bad state.
  timeout = 0
  instret = 0
  # Let the CPU run for N instructions.
  while ni <= expected[ 'end' ]:
    # Let combinational logic settle before checking values.
    yield Settle()
    timeout = timeout + 1
    # Only check expected values once per instruction.
    ninstret = yield cpu.csr.minstret_instrs
    if ninstret != instret:
      ni += 1
      instret = ninstret
      timeout = 0
      # Check expected values, if any.
      yield from check_vals( expected, ni, cpu )
    elif timeout > 1000:
      f += 1
      print( "\033[31mFAIL: Timeout\033[0m" )
      break
    # Step the simulation.
    yield Tick()

# Helper method to simulate running a CPU with the given ROM image
# for the specified number of CPU cycles. The 'name' field is used
# for printing and generating the waveform filename: "cpu_[name].vcd".
def cpu_sim( test ):
  print( "\033[33mSTART\033[0m running '%s' program:"%test[ 0 ] )
  # Create the CPU device.
  dut = CPU( ROM( test[ 2 ] ) )
  cpu = ResetInserter( dut.clk_rst )( dut )

  # Run the simulation.
  sim_name = "%s.vcd"%test[ 1 ]
  with Simulator( cpu, vcd_file = open( sim_name, 'w' ) ) as sim:
    def proc():
      # Initialize RAM values.
      for i in range( len( test[ 3 ] ) ):
        yield cpu.mem.ram.data[ i ].eq( LITTLE_END( test[ 3 ][ i ] ) )
      # Run the program and print pass/fail for individual tests.
      yield from cpu_run( cpu, test[ 4 ] )
      print( "\033[35mDONE\033[0m running %s: executed %d instructions"
             %( test[ 0 ], test[ 4 ][ 'end' ] ) )
    sim.add_clock( 1 / 6000000 )
    sim.add_sync_process( proc )
    sim.run()

# Helper method to simulate running a CPU from simulated SPI
# Flash which contains a given ROM image.
def cpu_spi_sim( test ):
  print( "\033[33mSTART\033[0m running '%s' program (SPI):"%test[ 0 ] )
  # Create the CPU device.
  sim_spi_off = ( 2 * 1024 * 1024 )
  dut = CPU( SPI_ROM( sim_spi_off, sim_spi_off + 1024, test[ 2 ] ) )
  cpu = ResetInserter( dut.clk_rst )( dut )

  # Run the simulation.
  sim_name = "%s_spi.vcd"%test[ 1 ]
  with Simulator( cpu, vcd_file = open( sim_name, 'w' ) ) as sim:
    def proc():
      for i in range( len( test[ 3 ] ) ):
        yield cpu.mem.ram.data[ i ].eq( test[ 3 ][ i ] )
      yield from cpu_run( cpu, test[ 4 ] )
      print( "\033[35mDONE\033[0m running %s: executed %d instructions"
             %( test[ 0 ], test[ 4 ][ 'end' ] ) )
    sim.add_clock( 1 / 6000000 )
    sim.add_sync_process( proc )
    sim.run()

from tests.test_roms.rv32i_add import *
from tests.test_roms.rv32i_addi import *
from tests.test_roms.rv32i_and import *
from tests.test_roms.rv32i_andi import *
from tests.test_roms.rv32i_auipc import *
from tests.test_roms.rv32i_beq import *
from tests.test_roms.rv32i_bge import *
from tests.test_roms.rv32i_bgeu import *
from tests.test_roms.rv32i_blt import *
from tests.test_roms.rv32i_bltu import *
from tests.test_roms.rv32i_bne import *
from tests.test_roms.rv32i_delay_slots import *
from tests.test_roms.rv32i_ebreak import *
from tests.test_roms.rv32i_ecall import *
from tests.test_roms.rv32i_endianess import *
from tests.test_roms.rv32i_io import *
from tests.test_roms.rv32i_jal import *
from tests.test_roms.rv32i_jalr import *
from tests.test_roms.rv32i_lb import *
from tests.test_roms.rv32i_lbu import *
from tests.test_roms.rv32i_lh import *
from tests.test_roms.rv32i_lhu import *
from tests.test_roms.rv32i_lw import *
from tests.test_roms.rv32i_lui import *
from tests.test_roms.rv32i_misalign_jmp import *
from tests.test_roms.rv32i_misalign_ldst import *
from tests.test_roms.rv32i_nop import *
from tests.test_roms.rv32i_or import *
from tests.test_roms.rv32i_ori import *
from tests.test_roms.rv32i_rf_size import *
from tests.test_roms.rv32i_rf_width import *
from tests.test_roms.rv32i_rf_x0 import *
from tests.test_roms.rv32i_sb import *
from tests.test_roms.rv32i_sh import *
from tests.test_roms.rv32i_sw import *
from tests.test_roms.rv32i_sll import *
from tests.test_roms.rv32i_slli import *
from tests.test_roms.rv32i_slt import *
from tests.test_roms.rv32i_slti import *
from tests.test_roms.rv32i_sltu import *
from tests.test_roms.rv32i_sltiu import *
from tests.test_roms.rv32i_sra import *
from tests.test_roms.rv32i_srai import *
from tests.test_roms.rv32i_srl import *
from tests.test_roms.rv32i_srli import *
from tests.test_roms.rv32i_sub import *
from tests.test_roms.rv32i_xor import *
from tests.test_roms.rv32i_xori import *

# 'main' method to run a basic testbench.
if __name__ == "__main__":
  if ( len( sys.argv ) == 2 ) and ( sys.argv[ 1 ] == '-b' ):
    # Build the application for an iCE40UP5K FPGA.
    # Currently, this is meaningless, because it builds the CPU
    # with a hard-coded 'infinite loop' ROM. But it's a start.
    with warnings.catch_warnings():
      warnings.filterwarnings( "ignore", category = DriverConflict )
      warnings.filterwarnings( "ignore", category = UnusedElaboratable )
      # Build the CPU to read its program from a 2MB offset in SPI Flash.
      prog_start = ( 2 * 1024 * 1024 )
      cpu = CPU( SPI_ROM( prog_start, prog_start * 2, None ) )
      UpduinoPlatform().build( ResetInserter( cpu.clk_rst )( cpu ),
                               do_program = False )
  else:
    # Run testbench simulations.
    with warnings.catch_warnings():
      warnings.filterwarnings( "ignore", category = DriverConflict )

      print( '--- CPU Tests ---' )
      # Simulate the 'infinite loop' ROM to screen for syntax errors.
      cpu_sim( loop_test )
      cpu_spi_sim( loop_test )
      cpu_sim( ram_pc_test )
      cpu_spi_sim( ram_pc_test )
      # Simulate the RV32I compliance tests.
      cpu_sim( add_test )
      cpu_sim( addi_test )
      cpu_sim( and_test )
      cpu_sim( andi_test )
      cpu_sim( auipc_test )
      cpu_sim( beq_test )
      cpu_sim( bge_test )
      cpu_sim( bgeu_test )
      cpu_sim( blt_test )
      cpu_sim( bltu_test )
      cpu_sim( bne_test )
      cpu_sim( delay_slots_test )
      cpu_sim( ebreak_test )
      cpu_sim( ecall_test )
      cpu_sim( endianess_test )
      cpu_sim( io_test )
      cpu_sim( jal_test )
      cpu_sim( jalr_test )
      cpu_sim( lb_test )
      cpu_sim( lbu_test )
      cpu_sim( lh_test )
      cpu_sim( lhu_test )
      cpu_sim( lw_test )
      cpu_sim( lui_test )
      cpu_sim( misalign_jmp_test )
      cpu_sim( misalign_ldst_test )
      cpu_sim( nop_test )
      cpu_sim( or_test )
      cpu_sim( ori_test )
      cpu_sim( rf_size_test )
      cpu_sim( rf_width_test )
      cpu_sim( rf_x0_test )
      cpu_sim( sb_test )
      cpu_sim( sh_test )
      cpu_sim( sw_test )
      cpu_sim( sll_test )
      cpu_sim( slli_test )
      cpu_sim( slt_test )
      cpu_sim( slti_test )
      cpu_sim( sltu_test )
      cpu_sim( sltiu_test )
      cpu_sim( sra_test )
      cpu_sim( srai_test )
      cpu_sim( srl_test )
      cpu_sim( srli_test )
      cpu_sim( sub_test )
      cpu_sim( xor_test )
      cpu_sim( xori_test )

      # Done; print results.
      print( "CPU Tests: %d Passed, %d Failed"%( p, f ) )
