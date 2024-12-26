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

def generateFrame(packet: LedPacket):
    cmd = packet.cmd & 0xFF
    frame = bytes([packet.head, cmd]) + bytes(packet.payload)
    # pad frame data to 19 bytes (plus checksum)
    frame += bytes([0] * (19 - len(frame)))
    frame += generateChecksum(frame)

class GoveeAPI:
    def __init__(self, ble_device: BleakClient, address: str, segmented: bool = False):
        self._conn = None
        self._ble_device = ble_device
        self._address = address
        self._segmented = segmented
        self._packet_buffer = []

    async def _preparePacket(self, packet: LedPacket):
        self._packet_buffer.append(packet)
    
    async def _getClient(self):
        return await bleak_retry_connector.establish_connection(BleakClient, self._ble_device, self._address)
    
    async def sendPacketBuffer(self):
        if len(self._packet_buffer) == 0:
            return None #nothing to do
        async with await self._getClient() as client:
            for packet in self._packet_buffer:
                frame = generateFrame(packet)
                await client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, frame, False)
            self._packet_buffer = []

    async def requestStateBuffered(self):
        packet = LedPacket(LedPacketHead.REQUEST, LedPacketCmd.POWER)
        await self._preparePacket(packet)

    async def requestBrightnessBuffered(self):
        packet = LedPacket(LedPacketHead.REQUEST, LedPacketCmd.BRIGHTNESS)
        await self._preparePacket(packet)

    async def requestColorBuffered(self):
        if self._segmented:
            #only request first segment
            packet = LedPacket(LedPacketHead.REQUEST, LedPacketCmd.SEGMENT, b'\x01')
            await self._preparePacket(packet)
        else:
            packet = LedPacket(LedPacketHead.REQUEST, LedPacketCmd.COLOR)
            await self._preparePacket(packet)
    
    async def setStateBuffered(self, state: bool):
        packet = LedPacket(LedPacketHead.COMMAND, LedPacketCmd.POWER, [0x1 if state else 0x0)
        await self._preparePacket(packet)
    
    async def setBrightnessBuffered(self, value: int):
        if not 0 <= value <= 255:
            raise ValueError(f'Brightness out of range: {value}')

        if self._segmented:
            # brightnessPercent
            value = int(value/255.0*100)
        else:
            value = round(value)
            
        packet = LedPacket(LedPacketHead.COMMAND, LedPacketCmd.BRIGHTNESS, [value])
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
        packet = LedPacket(LedPacketHead.COMMAND, LedPacketCmd.COLOR, payload)
        await self._preparePacket(packet)
