#!/usr/bin/env python3

import argparse
import cmd
import sys
import time
import zlib
from os import path
from struct import pack
from time import sleep

import serial
from messages import Cmd, Messages, MsgType

print("""
 ██████╗ ██╗   ██╗██╗ ██████╗██╗  ██╗██████╗  ██████╗  ██████╗ ████████╗
██╔═══██╗██║   ██║██║██╔════╝██║ ██╔╝██╔══██╗██╔═══██╗██╔═══██╗╚══██╔══╝
██║   ██║██║   ██║██║██║     █████╔╝ ██████╔╝██║   ██║██║   ██║   ██║   
██║▄▄ ██║██║   ██║██║██║     ██╔═██╗ ██╔══██╗██║   ██║██║   ██║   ██║   
╚██████╔╝╚██████╔╝██║╚██████╗██║  ██╗██████╔╝╚██████╔╝╚██████╔╝   ██║   
 ╚══▀▀═╝  ╚═════╝ ╚═╝ ╚═════╝╚═╝  ╚═╝╚═════╝  ╚═════╝  ╚═════╝    ╚═╝                                                                           
""")


class QuickbootClient:
    """Communicates with the Quickboot bootloader over a serial connection.

    Sends/receives raw bytes and commands to the bootloader. The following commands are supported:
        - WRITE: Send a message to the bootloader inbox
        - LIST: List messages in the bootloader outbox
        - READ: Read a message from the bootloader outbox

    Args:
        port (str): Serial port to connect to (e.g., '/dev/ttyACM0')
        baudrate (int, optional): Baud rate for the serial connection. Defaults to 115200.
    """

    def __init__(self, port: str, baudrate: int = 115200) -> None:
        self.ser = serial.Serial(port, baudrate, timeout=5)
        self.ser.flush()

    def send(self, data: bytes) -> None:
        """Send raw bytes to the bootloader.

        Args:
            data (bytes): Raw bytes to send

        Returns: None
        """
        self.ser.write(data)
        self.ser.flush()

    def send_cmd(self, cmd: Cmd, data: bytes) -> None:
        """Send a command to the bootloader.

        Args:
            cmd (Cmd): Command to send
            data (bytes): Data to send

        Returns: None
        """
        packet = pack("<I", cmd)
        packet += pack("<I", len(data))
        packet += data
        self.send(packet)

        time.sleep(0.1)  # Allow time for the command to be processed

    def recv(self, len: int = 4096):
        """Receive raw bytes from the bootloader.

        Args:
            len (int, optional): Number of bytes to read. Defaults to 4096.

        Returns: bytes: Received bytes
        """
        return self.ser.read(len)

    def close(self) -> None:
        """Close the serial connection."""
        self.ser.close()


class CmdLine(cmd.Cmd):
    """Simple command line interface for interacting with the Quickboot bootloader.

    Commands:
        lock_state          - Print the current bootloader lock state
        get_vars            - Print bootloader variables
        current_slot        - Print the current active boot slot
        change_slot <A|B>   - Change the active boot slot (A or B)
        boot <filename>     - Boot a specified image file
        exit                - Exit the Quickboot client shell

    Args:
        client (QuickbootClient): Instance of QuickbootClient to communicate with the bootloader
    """

    intro = "Welcome to the Quickboot client shell. Type help or ? to list commands.\n"
    prompt = "(quickboot) "

    def __init__(self, client: QuickbootClient):
        super().__init__()
        self.client = client
        self.messages = Messages(client)

    def do_lock_state(self, arg: str) -> None:
        "Print the current bootloader lock state"
        self.messages.send(MsgType.LOCK_STATE, b"")

    def do_get_vars(self, arg: str) -> None:
        "Print bootloader variables"
        self.messages.send(MsgType.GET_VARS, b"")

    def do_current_slot(self, arg: str) -> None:
        "Print the current active boot slot"
        self.messages.send(MsgType.CURRENT_SLOT, b"")

    def do_change_slot(self, arg: str) -> None:
        "Change the active boot slot (A or B)"
        args = arg.split()
        if len(args) != 1:
            print("Usage: change_slot <slot>")
            return

        slot = args[0][0].encode()
        self.messages.send(MsgType.CHANGE_SLOT, slot)

    def do_boot(self, arg: str) -> None:
        "Boot a specified image file (boot <filename>)"
        args = arg.split()
        if len(args) != 1:
            print("Usage: boot <filename>")
            return

        if not path.isfile(args[0]):
            print(f"File not found: {args[0]}", file=sys.stderr)
            return

        with open(args[0], "rb") as f:
            data = f.read()

        payload = pack("<I", len(data))
        payload += pack("<I", zlib.crc32(data))
        self.messages.send(MsgType.BOOT, payload)
        self.client.send(data)
        sleep(0.5)

    def do_exit(self, arg: str) -> bool:
        "Exit the Quickboot client shell"
        print("Exiting...")
        return True

    def postcmd(self, stop: bool, line: str) -> bool:
        """Reads all new messages in the outbox from the bootloader
        and processes them using the appropriate handler."""
        self.messages.process()
        return super().postcmd(stop, line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quickboot Client")
    parser.add_argument(
        "--port",
        type=str,
        help="Serial port to connect to",
        default="/dev/ttyACM0",
    )
    parser.add_argument(
        "--baudrate",
        type=int,
        default=115200,
        help="Baud rate for serial communication",
    )
    args = parser.parse_args()

    client = QuickbootClient(args.port, args.baudrate)
    messages = Messages(client)
    cmd = CmdLine(client)
    cmd.cmdloop()
