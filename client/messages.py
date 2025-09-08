"""Quickboot message handling module

The Quickboot bootloader implements an asynchronous message-based protocol. Incoming and
outgoing messages are stored in an inbox/outbox. The host queries the outbox for new
messages.


A Message consists of a Header appended with arbitrary length data. A CRC32 is calculated
over the data and stored in the header. Each message has it's own handler function that is
called based on the message type.

"""

import sys
import zlib
from enum import IntEnum
from struct import pack

import cstruct


class Cmd(IntEnum):
    """Supported bootloader commands."""

    WRITE = 0
    READ = 1
    LIST = 2


class Header(cstruct.MemCStruct):
    """The message header structure."""

    msg_magic = b"MSG!"
    msg_version = 1
    __byte_order__ = cstruct.LITTLE_ENDIAN
    __def__ = """
        struct msg_header {
        unsigned char magic[4];
        uint32_t version;   // Protocol version
        uint32_t id;        // Message identifier
        uint32_t type;      // Message type
        uint32_t flags;     // Message specific flags
        uint32_t len;       // Length of the message data
        uint32_t crc32;     // crc32 of the message data        
        }
    """

    def __init__(self):
        super().__init__()
        self.magic = self.msg_magic
        self.version = self.msg_version
        self.id = 0
        self.type = 0
        self.flags = 0
        self.len = 0
        self.crc32 = 0

    def __str__(self):
        return f"Header(magic={self.magic}, version={self.version}, id={self.id}, type={self.type}, flags={self.flags}, len={self.len}, crc32={hex(self.crc32)})"


class Message:
    """A Message consists of a Header and data."""

    header: Header
    data: bytes

    def __init__(self, header: Header, data: bytes):
        self.header = header
        self.data = data


class MessageBox:
    """A MessageBox contains a list of messages and tracks the last processed message ID."""

    messages: list[Message]
    last_id: int

    def __init__(self):
        self.messages = []
        self.last_id = 0


class MsgType(IntEnum):
    """Message types that can be sent/received."""

    ERROR = 0
    ECHO = 1
    LOCK_STATE = 2
    GET_VARS = 3
    CURRENT_SLOT = 4
    CHANGE_SLOT = 5
    BOOT = 6
    EMPTY = 7


class MsgFlags(IntEnum):
    """Flags that can be set on messages."""

    FLAG_ORIGIN_HOST = 1
    FLAG_ORIGIN_TARGET = 1 << 1
    INVALID = 1 << 2
    INVALID_MAGIC = 1 << 3
    INVALID_VERSION = 1 << 4
    INVALID_CRC = 1 << 5
    INVALID_PAYLOAD_SIZE = 1 << 6
    NO_HANDLER = 1 << 7
    INVALID_SLOT = 1 << 8
    BOOTLOADER_LOCKED = 1 << 9
    IMAGE_TOO_LARGE = 1 << 10
    OUT_OF_MEMORY = 1 << 11


class Messages:
    """Handles sending and receiving messages to/from the bootloader.

    Args:
        client (QuickbootClient): Instance of QuickbootClient to communicate with the bootloader

    """

    def __init__(self, client):
        self.client = client
        self.msgbox = MessageBox()
        self.boot_image = b""

    def send(self, type: int, data: bytes) -> None:
        """Sends a message to the bootloader inbox."""
        h = Header()
        h.len = len(data)
        h.crc32 = zlib.crc32(data)
        h.type = type

        packet = h.pack()
        packet += data
        self.client.send_cmd(Cmd.WRITE, packet)

    def list_outbox(self) -> list[Header]:
        """Lists the messages in the bootloader outbox."""
        self.client.send_cmd(Cmd.LIST, b"")

        # Read the number of messages
        data = self.client.recv(4)
        num_messages = int.from_bytes(data, "little")
        headers = []

        for _ in range(num_messages):
            header_data = self.client.recv(Header.sizeof())
            header = Header()
            header.unpack(header_data)
            headers.append(header)

        return headers

    def read(self, header: Header) -> bytes:
        """Reads the data associated with a message header.

        Args:
            header (Header): The header associated with the message to read

        Returns: bytes: The message data

        Raises: ValueError: If the message data is invalid
        """
        self.client.send_cmd(Cmd.READ, pack("<I", header.id))
        data = self.client.recv(header.len)
        if len(data) != header.len:
            raise ValueError(f"Expected {header.len} bytes, got {len(data)} bytes")

        if zlib.crc32(data) != header.crc32:
            raise ValueError(
                f"CRC32 mismatch: expected {hex(header.crc32)}, got {hex(zlib.crc32(data))}"
            )

        return data

    def check_flags(self, msg: Message) -> None:
        """Check and print message flags for errors."""
        if msg.header.type == MsgType.ERROR:
            print(
                f"Message [{msg.header.id}] an error occurred while handling a valid message",
                file=sys.stderr,
            )

        if msg.header.flags & MsgFlags.INVALID:
            print(
                f"Message [{msg.header.id}] was not processed correctly",
                file=sys.stderr,
            )

        if msg.header.flags & MsgFlags.INVALID_MAGIC:
            print("Reason: Invalid message magic", file=sys.stderr)

        if msg.header.flags & MsgFlags.INVALID_VERSION:
            print("Reason: Invalid message version", file=sys.stderr)

        if msg.header.flags & MsgFlags.INVALID_CRC:
            print("Reason: Invalid message CRC", file=sys.stderr)

        if msg.header.flags & MsgFlags.INVALID_PAYLOAD_SIZE:
            print("Reason: Invalid payload size", file=sys.stderr)

        if msg.header.flags & MsgFlags.NO_HANDLER:
            print("Reason: No handler for this message type", file=sys.stderr)

        if msg.header.flags & MsgFlags.INVALID_SLOT:
            print("Reason: Invalid slot", file=sys.stderr)

        if msg.header.flags & MsgFlags.BOOTLOADER_LOCKED:
            print("Reason: Bootloader is locked", file=sys.stderr)

        if msg.header.flags & MsgFlags.IMAGE_TOO_LARGE:
            print("Reason: Image too large", file=sys.stderr)

        if msg.header.flags & MsgFlags.OUT_OF_MEMORY:
            print("Reason: Out of memory", file=sys.stderr)

    def process(self):
        """Processes all new messages in the outbox from the bootloader.

        First lists all messages in the outbox. We then check if there are any new messages
        based on the message ID. We ignore messages that have already been read and are
        marked as empty.

        Messages that have the ERROR flag set are processed by check_flags(). Other messages are
        processed by calling the appropriate handler function based on the message type.
        """
        # Retrieve the latest message, ignore empty messages
        for h in self.list_outbox():
            if h.id > self.msgbox.last_id and h.type != MsgType.EMPTY:
                if h.flags & MsgFlags.INVALID:
                    self.msgbox.messages.append(Message(h, b""))
                else:
                    try:
                        self.msgbox.messages.append(Message(h, self.read(h)))
                    except ValueError as e:
                        print(f"Error processing message {h.id}: {e}")

        # Execute each handler
        for msg in self.msgbox.messages:
            self.msgbox.last_id = msg.header.id
            try:
                if msg.header.type == MsgType.EMPTY:
                    continue
                elif (
                    msg.header.type == MsgType.ERROR
                    or msg.header.flags & MsgFlags.INVALID
                ):
                    self.check_flags(msg)
                else:
                    handler = msg_types[msg.header.type]
                    handler(self, msg.data)
            except KeyError:
                print(f"No handler for message type {msg.header.type}")
            except Exception as e:
                print(f"Error processing message {msg.header.id}: {e}")

        self.msgbox.messages = []  # Clear inbox after processing


def msg_echo(messages: Messages, data: bytes):
    """Print the data that was echoed back from the bootloader."""
    print(f"Echo: {data.decode()}")


def msg_lock_state(messages: Messages, data: bytes):
    """Print the current bootloader lock state."""
    lock_state = int.from_bytes(data, "little")
    if lock_state == 0:
        print("Bootloader is locked")
    else:
        print("Bootloader is unlocked")


def msg_get_vars(messages: Messages, data: bytes):
    """Prints the bootloader variables."""
    print(data.decode())


def msg_current_slot(messages: Message, data: bytes):
    """Print the current active boot slot."""
    print(f"Current slot: {data.decode()}")


def msg_change_slot(messages: Messages, data: bytes):
    """Print the new active boot slot."""
    print(f"Current slot: {data.decode()}")


def msg_boot(messages: Messages, data: bytes):
    """Indicates that the boot image has been executed.

    Only happens if the boot image hands control back to the bootloader.
    This is unlikely to happen.
    """
    print("Boot image has been executed")


msg_types = {
    int(MsgType.ECHO): msg_echo,
    int(MsgType.LOCK_STATE): msg_lock_state,
    int(MsgType.GET_VARS): msg_get_vars,
    int(MsgType.CURRENT_SLOT): msg_current_slot,
    int(MsgType.CHANGE_SLOT): msg_change_slot,
    int(MsgType.BOOT): msg_boot,
}
