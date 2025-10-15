from enum import IntEnum
from dataclasses import dataclass

class LedPacketHead(IntEnum):
    COMMAND = 0x33
    REQUEST = 0xaa

class LedPacketCmd(IntEnum):
    POWER      = 0x01
    BRIGHTNESS = 0x04
    COLOR      = 0x05
    SEGMENT    = 0xa5
    MUSIC_MODE = 0x06
    EFFECT     = 0x07
    SCENE      = 0x08

class LedColorType(IntEnum):
    SEGMENTS    = 0x15
    SINGLE      = 0x02
    LEGACY      = 0x0D

class MusicModeType(IntEnum):
    OFF = 0x00
    RHYTHM = 0x01
    SPROUTING = 0x02
    SHINY = 0x03
    BEAT = 0x04
    WAVES = 0x05
    SPECTRUM = 0x06
    ROLLING = 0x07
    HOPPING = 0x08
    STARLIGHT = 0x09
    PIANO_KEYS = 0x0A
    JUMPING = 0x0B
    LUMINOUS = 0x0C

class CarnivalModeType(IntEnum):
    BRILLIANT = 0x10
    PULSATE = 0x11
    DAZZLE = 0x12
    FASCINATION = 0x13
    ASPIRING = 0x14
    CADENCE = 0x15
    REVEL = 0x16
    FLUCTUATE = 0x17
    FUNNY = 0x18
    SHIMMER = 0x19

class BasicModeType(IntEnum):
    DYNAMIC = 0x20
    CALM = 0x21

# Combined effect mapping for Home Assistant
EFFECT_MAP = {
    # Music reactive modes
    "Rhythm": MusicModeType.RHYTHM,
    "Sprouting": MusicModeType.SPROUTING,
    "Shiny": MusicModeType.SHINY,
    "Beat": MusicModeType.BEAT,
    "Waves": MusicModeType.WAVES,
    "Spectrum": MusicModeType.SPECTRUM,
    "Rolling": MusicModeType.ROLLING,
    "Hopping": MusicModeType.HOPPING,
    "Starlight": MusicModeType.STARLIGHT,
    "Piano Keys": MusicModeType.PIANO_KEYS,
    "Jumping": MusicModeType.JUMPING,
    "Luminous": MusicModeType.LUMINOUS,
    
    # Carnival modes
    "Brilliant": CarnivalModeType.BRILLIANT,
    "Pulsate": CarnivalModeType.PULSATE,
    "Dazzle": CarnivalModeType.DAZZLE,
    "Fascination": CarnivalModeType.FASCINATION,
    "Aspiring": CarnivalModeType.ASPIRING,
    "Cadence": CarnivalModeType.CADENCE,
    "Revel": CarnivalModeType.REVEL,
    "Fluctuate": CarnivalModeType.FLUCTUATE,
    "Funny": CarnivalModeType.FUNNY,
    "Shimmer": CarnivalModeType.SHIMMER,
    
    # Basic modes
    "Dynamic": BasicModeType.DYNAMIC,
    "Calm": BasicModeType.CALM,
}

@dataclass
class LedPacket:
    #request data or perform a change
    head: LedPacketHead
    #data to request or command to perform
    cmd: LedPacketCmd
    #actual data to transmit
    payload: bytes | list = b''

class GoveeUtils:
    @staticmethod
    async def generateChecksum(frame: bytes):
        """ returns checksum by XORing all data bytes """
        checksum = 0
        for b in frame:
            checksum ^= b
        #pad response to 8 bits
        return bytes([checksum & 0xFF])

    @staticmethod
    async def generateFrame(packet: LedPacket):
        """ returns transmittable frame bytes """
        #pad cmd to 8 bits
        cmd = packet.cmd & 0xFF
        #combine segments
        frame = bytes([packet.head, cmd]) + bytes(packet.payload)
        #pad frame data to 19 bytes (plus checksum)
        frame += bytes([0] * (19 - len(frame)))
        #add checksum to end
        frame += await GoveeUtils.generateChecksum(frame)
        return frame

    @staticmethod
    async def verifyChecksum(frame: bytes):
        checksum_received = frame[-1].to_bytes(1, 'big')
        checksum_calculated = await GoveeUtils.generateChecksum(frame[:-1])
        return checksum_received == checksum_calculated
