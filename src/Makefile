CFLAGS  ?=  -W -Wall -Wextra -Werror -Wundef -Wshadow -Wdouble-promotion \
            -Wformat-truncation -fno-common -Wconversion \
            -g3 -O0 -ffunction-sections -fdata-sections -I. -Ilib \
            -mcpu=cortex-m3 -mthumb $(EXTRA_CFLAGS)
LDFLAGS ?= -Tlink.ld -nostartfiles -nostdlib --specs nano.specs -lc -lgcc -Wl,--gc-sections -Wl,-Map=out/$@.map
SOURCES = lib/newlib/syscalls.c \
			lib/hal/gpio/gpio.c \
			lib/hal/pwr/pwr.c \
			lib/hal/timer/systick.c \
			lib/hal/uart/uart.c \
			lib/hal/led/led.c \
			lib/util/sleep/sleep.c \
			lib/util/crc32/crc32.c \
			lib/cmd/cmd.c \
			lib/msg/msg.c \
			lib/commands/echo/echo.c \
			lib/commands/bootloader/bootloader.c \
			lib/commands/getvars/getvars.c \
			lib/commands/slot/slot.c \
			main.c 
all: firmware.bin
build: firmware.bin

firmware.elf: $(SOURCES)
	arm-none-eabi-gcc $(SOURCES) $(CFLAGS) $(LDFLAGS) -o out/$@

firmware.bin: firmware.elf
	arm-none-eabi-objcopy -O binary out/$< out/$@

clean:
	rm -f out/firmware.*
