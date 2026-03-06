# Background
A government agency has confiscated an embedded device that uses the Quickboot bootloader. Our goal is to obtain code execution on the device. We've flashed the bootloader onto a NUCLEO F103RB reference device.

The reference device exposes a J-Link and serial device when connected to the host:

```
[ 7786.731817] usb 1-7.2.3: new full-speed USB device number 26 using xhci_hcd
[ 7786.821742] usb 1-7.2.3: New USB device found, idVendor=1366, idProduct=0105, bcdDevice= 1.00
[ 7786.821757] usb 1-7.2.3: New USB device strings: Mfr=1, Product=2, SerialNumber=3
[ 7786.821763] usb 1-7.2.3: Product: J-Link
[ 7786.821790] usb 1-7.2.3: Manufacturer: SEGGER
[ 7786.821797] usb 1-7.2.3: SerialNumber: 000773128126
[ 7786.836780] cdc_acm 1-7.2.3:1.0: ttyACM0: USB ACM device
```
You can interact with the bootloader using the Quickboot client:
```
 ██████╗ ██╗   ██╗██╗ ██████╗██╗  ██╗██████╗  ██████╗  ██████╗ ████████╗
██╔═══██╗██║   ██║██║██╔════╝██║ ██╔╝██╔══██╗██╔═══██╗██╔═══██╗╚══██╔══╝
██║   ██║██║   ██║██║██║     █████╔╝ ██████╔╝██║   ██║██║   ██║   ██║   
██║▄▄ ██║██║   ██║██║██║     ██╔═██╗ ██╔══██╗██║   ██║██║   ██║   ██║   
╚██████╔╝╚██████╔╝██║╚██████╗██║  ██╗██████╔╝╚██████╔╝╚██████╔╝   ██║   
 ╚══▀▀═╝  ╚═════╝ ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚═════╝    ╚═╝                                                                           

usage: quickboot.py [-h] [--port PORT] [--baudrate BAUDRATE]

Quickboot Client

options:
  -h, --help           show this help message and exit
  --port PORT          Serial port to connect to
  --baudrate BAUDRATE  Baud rate for serial communication
```

The client connects to */dev/ttyACM0* by default.

# Goal
Turn on the green LED (LD2) to prove that you have code execution. This can be done by writing the value **0x20** to address **0x40010810**. Or by calling some function that does this for you. The exploit should solely use the interface provided over the serial connection.

# Requirements

## Building

To build the source code ensure that you have the following package(s) installed:
```
$ sudo apt install gcc-arm-none-eabi
```

## JLink
You'll need the JLink utilities installed on your machine to use the debugger or (re-)flash firmware. Download the lastest version for your operating system from:

- <https://www.segger.com/downloads/jlink/>

```
$ sudo dpkg -i JLink_Linux_V858_x86_64.deb 
[sudo] password for user: 
(Reading database ... 744293 files and directories currently installed.)
Preparing to unpack JLink_Linux_V858_x86_64.deb ...
Removing /opt/SEGGER/JLink ...
Unpacking jlink (8.58.0) over (8.24.0) ...
Setting up jlink (8.58.0) ...
Updating udev rules via udevadm...
OK
$ which JLinkGDBServer JLinkExe
/usr/bin/JLinkGDBServer
/usr/bin/JLinkExe
```

## Python
The scripts in this reposity were tested using Python version 3.12.3. Install the additional required Python packages inside a virtual environment:
```
$ python3 -m venv env
$ source env/bin/activate
$ pip3 install -r requirements.txt 
Collecting cstruct==6.1 (from -r requirements.txt (line 1))
  Using cached cstruct-6.1-py2.py3-none-any.whl.metadata (14 kB)
Collecting pyserial==3.5 (from -r requirements.txt (line 2))
  Using cached pyserial-3.5-py2.py3-none-any.whl.metadata (1.6 kB)
Using cached cstruct-6.1-py2.py3-none-any.whl (32 kB)
Using cached pyserial-3.5-py2.py3-none-any.whl (90 kB)
Installing collected packages: pyserial, cstruct
Successfully installed cstruct-6.1 pyserial-3.5
```

# Firmware
## Building
To build the firmware navigate to the **src** directory and run the *make* command:

```
$ cd src
$ make 
arm-none-eabi-gcc lib/newlib/syscalls.c lib/hal/gpio/gpio.c lib/hal/pwr/pwr.c lib/hal/timer/systick.c lib/hal/uart/uart.c lib/hal/led/led.c lib/util/sleep/sleep.c lib/util/crc32/crc32.c lib/cmd/cmd.c lib/msg/msg.c lib/commands/echo/echo.c lib/commands/bootloader/bootloader.c lib/commands/getvars/getvars.c lib/commands/slot/slot.c main.c  -W -Wall -Wextra -Werror -Wundef -Wshadow -Wdouble-promotion -Wformat-truncation -fno-common -Wconversion -g3 -O0 -ffunction-sections -fdata-sections -I. -Ilib -mcpu=cortex-m3 -mthumb  -Tlink.ld -nostartfiles -nostdlib --specs nano.specs -lc -lgcc -Wl,--gc-sections -Wl,-Map=out/firmware.elf.map -o out/firmware.elf
arm-none-eabi-objcopy -O binary out/firmware.elf out/firmware.bin
```
The firmware for the NUCLEO-F103RB and the ELF file containing symbols, are stored in the **out** folder:
```
$ ls -l out 
total 272
-rwxrwxr-x 1 user user   9732 sep  8 12:42 firmware.bin
-rwxrwxr-x 1 user user 164584 sep  8 12:42 firmware.elf
-rw-rw-r-- 1 user user  96286 sep  8 12:42 firmware.elf.map
```
## Flashing
The firmware should already be flashed onto the NUCLEO-F103RB. Use the *JLinkExe* utility to re-flash the firmware if needed:
```
JLinkExe -device STM32F103C8 -if SWD -speed 4000 -autoconnect 1
..
..
loadbin bin/firmware.bin,08000000
r
g
```

# Debugging
First start the GDB server using *JLinkGDBServer*:
```
$ JLinkGDBServer -port 4444 -device STM32F103RB -USB
```
In a different window connect using *gdb-multiarch*:
```
$ gdb-multiarch src/out/firmware.elf
GNU gdb (Ubuntu 15.0.50.20240403-0ubuntu1) 15.0.50.20240403-git
Copyright (C) 2024 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.
Type "show copying" and "show warranty" for details.
This GDB was configured as "x86_64-linux-gnu".
Type "show configuration" for configuration details.
For bug reporting instructions, please see:
<https://www.gnu.org/software/gdb/bugs/>.
Find the GDB manual and other documentation resources online at:
    <http://www.gnu.org/software/gdb/documentation/>.

For help, type "help".
Type "apropos word" to search for commands related to "word"...
Reading symbols from src/out/firmware.elf...
(gdb)
```
# Troubleshooting
You'll probably need to reset the device a few times while researching the firmware. Press the **black** button to reset the device. The green LED should blink twice, indicating that the firmware has been initialized successfully.

# License
This is free and unencumbered software released into the public domain.

Anyone is free to copy, modify, publish, use, compile, sell, or
distribute this software, either in source code form or as a compiled
binary, for any purpose, commercial or non-commercial, and by any
means.

In jurisdictions that recognize copyright laws, the author or authors
of this software dedicate any and all copyright interest in the
software to the public domain. We make this dedication for the benefit
of the public at large and to the detriment of our heirs and
successors. We intend this dedication to be an overt act of
relinquishment in perpetuity of all present and future rights to this
software under copyright law.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

For more information, please refer to <https://unlicense.org/>