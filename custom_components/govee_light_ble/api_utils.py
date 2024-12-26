from enum import IntEnu
from dataclasses import dataclass

class LedPacketHead(IntEnum):
    COMMAND = 0x33
    REQUEST = 0xaa

class LedPacketCmd(IntEnum):
    POWER      = 0x01
    BRIGHTNESS = 0x04
    COLOR      = 0x05
    SEGMENT    = 0xa5

class LedColorType(IntEnum):
    SEGMENTS    = 0x15
    SINGLE      = 0x02

@dataclass
class LedPacket:
    head: LedPacketHead
    cmd: LedPacketCmd
    payload: bytes | list = b''

class GoveeUtils:
    @staticmethod
    def generateChecksum(frame: bytes):
        # The checksum is calculated by XORing all data bytes
        checksum = 0
        for b in frame:
            checksum ^= b
        return bytes([checksum & 0xFF])

    @staticmethod
    def generateFrame(packet: LedPacket):
        cmd = packet.cmd & 0xFF
        frame = bytes([packet.head, cmd]) + bytes(packet.payload)
        # pad frame data to 19 bytes (plus checksum)
        frame += bytes([0] * (19 - len(frame)))
        frame += GoveeUtils.generateChecksum(frame)
