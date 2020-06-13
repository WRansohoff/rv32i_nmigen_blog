# GCC toolchain programs.
CC = riscv32-unknown-elf-gcc
OC = riscv32-unknown-elf-objcopy
OS = riscv32-unknown-elf-size

# Assembly directives.
ASFLAGS += -c
ASFLAGS += -O0
ASFLAGS += -Wall
ASFLAGS += -fmessage-length=0
ASFLAGS += -march=rv32imac
ASFLAGS += -mabi=ilp32
ASFLAGS += -mcmodel=medlow

# C compilation directives
CFLAGS += -c
CFLAGS += -Wall
CFLAGS += -O0
CFLAGS += -g
CFLAGS += -fmessage-length=0
CFLAGS += --specs=nosys.specs
CFLAGS += -march=rv32i
CFLAGS += -mabi=ilp32
CFLAGS += -mcmodel=medlow

# Linker directives.
LFLAGS += -Wall
LFLAGS += -Wl,--no-relax
LFLAGS += -Wl,--gc-sections
LFLAGS += -nostdlib
LFLAGS += -nostartfiles
LFLAGS += -lc
LFLAGS += -lgcc
LFLAGS += --specs=nosys.specs
LFLAGS += -march=rv32i
LFLAGS += -mabi=ilp32
LFLAGS += -mcmodel=medlow
LFLAGS += -T./../common/link.ld

# Extra header file include directories.
INCLUDE += -I./../common

# Source files.
AS_SRC  = ./../common/start.S
C_SRC   = ./main.c

# Object files to build.
OBJS    = $(AS_SRC:.S=.o)
OBJS   += $(C_SRC:.c=.o)

# Default rule to build the whole project.
.PHONY: all
all: main.bin

# Rule to build assembly files.
%.o: %.S
	$(CC) -x assembler-with-cpp $(ASFLAGS) $(INCLUDE) $< -o $@

# Rule to compile C files.
%.o: %.c
	$(CC) $(CFLAGS) $(INCLUDE) $< -o $@

# Rule to create an ELF file from the compiled object files.
main.elf: $(OBJS)
	$(CC) $^ $(LFLAGS) -o $@

# Rule to create a raw binary file from an ELF file.
main.bin: main.elf
	$(OC) -S -O binary $< $@
	$(OS) $<

# Rule to flash the program 2MB into the SPI Flash on an iCE40 board.
.PHONY: flash
flash: all
	iceprog -o 2M main.bin

# Rule to clear out generated build files.
.PHONY: clean
clean:
	rm -f $(OBJS)
	rm -f main.elf
	rm -f main.bin
