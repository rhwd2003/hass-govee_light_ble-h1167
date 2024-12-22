from enum import IntEnum
from colour import Color
import asyncio
import bleak_retry_connector
from bleak import BleakClient
from dataclasses import dataclass

from .const import WRITE_CHARACTERISTIC_UUID, READ_CHARACTERISTIC_UUID

class LedPacketHead(IntEnum):
    COMMAND = 0x33
    REQUEST = 0xaa

class LedPacketCmd(IntEnum):
    POWER      = 0x01
    BRIGHTNESS = 0x04
    COLOR      = 0x05

class LedColorType(IntEnum):
    SEGMENTS    = 0x15
    SINGLE      = 0x02

@dataclass
class LedPacket:
    head: LedPacketHead
    cmd: LedPacketCmd
    payload: bytes | list = b''

@dataclass
class LedFrame:
    uuid: str
    data: bytes

def generateChecksum(frame: bytes):
    # The checksum is calculated by XORing all data bytes
    checksum = 0
    for b in frame:
        checksum ^= b
    return bytes([checksum & 0xFF])

def getUUIDByHead(head: LedPacketHead):
    match head:
        case LedPacketHead.REQUEST:
            return READ_CHARACTERISTIC_UUID
        case _:
            return WRITE_CHARACTERISTIC_UUID

class GoveeAPI:
    def __init__(self, ble_device, address):
        self._conn = None
        self._ble_device = ble_device
        self._address = address
        self._frame_buffer = []
    
    async def _prepareWritePacket(self, packet: LedPacket):
        await self._preparePacket(WRITE_CHARACTERISTIC_UUID, packet)
    
    async def _prepareReadPacket(self, packet: LedPacket):
        await self._preparePacket(READ_CHARACTERISTIC_UUID, packet)

    async def _preparePacket(self, packet: LedPacket):
        uuid = getUUIDByHead(packet.head)
        cmd = packet.cmd & 0xFF
        payload = bytes(packet.payload)
        frame = bytes([packet.head, cmd]) + bytes(payload)
        # pad frame data to 19 bytes (plus checksum)
        frame += bytes([0] * (19 - len(frame)))
        frame += generateChecksum(frame)
        self._frame_buffer.append(
            LedFrame(uuid, frame)
        )
    
    async def _getClient(self):
        return await bleak_retry_connector.establish_connection(BleakClient, self._ble_device, self._address)

    async def sendPacketBuffer(self):
        if len(self._frame_buffer) == 0:
            return None #nothing to do
        async with await self._getClient() as client:
            for frame in self._frame_buffer:
                await client.write_gatt_char(frame.uuid, frame.data, False)
            self._frame_buffer = []
    
    async def setStateBuffered(self, state: bool):
        packet = LedPacket(
            head=LedPacketHead.COMMAND,
            cmd=LedPacketCmd.POWER,
            payload=[0x1 if state else 0x0]
        )
        await self._preparePacket(packet)
    
    async def setBrightnessBuffered(self, value: int):
        if not 0 <= value <= 255:
            raise ValueError(f'Brightness out of range: {value}')
        value = round(value)
        packet = LedPacket(
            head=LedPacketHead.COMMAND,
            cmd=LedPacketCmd.BRIGHTNESS,
            payload=[value]
        )
        await self._preparePacket(packet)
        
    async def setColorBuffered(self, red: int, green: int, blue: int, segmented: bool = False):
        if not 0 <= red <= 255:
            raise ValueError(f'Color out of range: {red}')
        if not 0 <= green <= 255:
            raise ValueError(f'Color out of range: {green}')
        if not 0 <= blue <= 255:
            raise ValueError(f'Color out of range: {blue}')
        payload = [LedColorType.SINGLE, red, green, blue]
        if segmented:
            payload = [LedColorType.SEGMENTS, 0x01, red, green, blue, 0, 0, 0, 0, 0, 0xff, 0xff]
        packet = LedPacket(
            head=LedPacketHead.COMMAND,
            cmd=LedPacketCmd.COLOR,
            payload=payload
        )
        await self._preparePacket(packet)
