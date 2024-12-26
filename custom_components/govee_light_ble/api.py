from enum import IntEnum
import asyncio
import bleak_retry_connector
from bleak import BleakClient, BLEDevice
from dataclasses import dataclass

from .const import WRITE_CHARACTERISTIC_UUID

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

def generateChecksum(frame: bytes):
    # The checksum is calculated by XORing all data bytes
    checksum = 0
    for b in frame:
        checksum ^= b
    return bytes([checksum & 0xFF])

class GoveeAPI:
    def __init__(self, ble_device: BleakClient, address: str, segmented: bool = False):
        self._conn = None
        self._ble_device = ble_device
        self._address = address
        self._segmented = segmented
        self._frame_buffer = []

    async def _preparePacket(self, packet: LedPacket):
        cmd = packet.cmd & 0xFF
        frame = bytes([packet.head, cmd]) + bytes(packet.payload)
        # pad frame data to 19 bytes (plus checksum)
        frame += bytes([0] * (19 - len(frame)))
        frame += generateChecksum(frame)
        self._frame_buffer.append(frame)

    async def _prepareRequestPacket(self, cmd: LedPacketCmd, payload: bytes = b''):
        packet = LedPacket(
            head=LedPacketHead.REQUEST,
            cmd=cmd,
            payload=payload
        )
        await self._preparePacket(packet)
    
    async def _getClient(self):
        return await bleak_retry_connector.establish_connection(BleakClient, self._ble_device, self._address)
    
    async def sendPacketBuffer(self):
        if len(self._frame_buffer) == 0:
            return None #nothing to do
        async with await self._getClient() as client:
            for frame in self._frame_buffer:
                await client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, frame, False)
            self._frame_buffer = []

    async def requestStateBuffered(self):
        await self._prepareRequestPacket(LedPacketCmd.POWER)

    async def requestBrightnessBuffered(self):
        await self._prepareRequestPacket(LedPacketCmd.BRIGHTNESS)

    async def requestColorBuffered(self):
        if self._segmented:
            await self._prepareRequestPacket(LedPacketCmd.SEGMENT, b'\x01')
            await self._prepareRequestPacket(LedPacketCmd.SEGMENT, b'\x02')
            await self._prepareRequestPacket(LedPacketCmd.SEGMENT, b'\x03')
            await self._prepareRequestPacket(LedPacketCmd.SEGMENT, b'\x04')
            await self._prepareRequestPacket(LedPacketCmd.SEGMENT, b'\x05')
        else:
            await self._prepareRequestPacket(LedPacketCmd.COLOR)
    
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

        if self._segmented:
            # brightnessPercent
            value = int(value/255.0*100)
        else:
            value = round(value)
            
        packet = LedPacket(
            head=LedPacketHead.COMMAND,
            cmd=LedPacketCmd.BRIGHTNESS,
            payload=[value]
        )
        await self._preparePacket(packet)
        
    async def setColorBuffered(self, red: int, green: int, blue: int):
        if not 0 <= red <= 255:
            raise ValueError(f'Color out of range: {red}')
        if not 0 <= green <= 255:
            raise ValueError(f'Color out of range: {green}')
        if not 0 <= blue <= 255:
            raise ValueError(f'Color out of range: {blue}')
        payload = [LedColorType.SINGLE, red, green, blue]
        if self._segmented:
            payload = [LedColorType.SEGMENTS, 0x01, red, green, blue, 0, 0, 0, 0, 0, 0xff, 0xff]
        packet = LedPacket(
            head=LedPacketHead.COMMAND,
            cmd=LedPacketCmd.COLOR,
            payload=payload
        )
        await self._preparePacket(packet)
