import asyncio
import bleak_retry_connector
from bleak import (
    BleakClient,
    BLEDevice
)
from .const import WRITE_CHARACTERISTIC_UUID
from .api_utils import (
    LedPacketHead,
    LedPacketCmd,
    LedColorType,
    LedPacket,
    GoveeUtils
)

class GoveeAPI:
    def __init__(self, ble_device: BleakClient, address: str, segmented: bool = False):
        self._conn = None
        self._ble_device = ble_device
        self._address = address
        self._segmented = segmented
        self._packet_buffer = []

    async def _getClient(self):
        return await bleak_retry_connector.establish_connection(BleakClient, self._ble_device, self._address)
    
    async def _preparePacket(self, cmd: LedPacketCmd, payload: bytes | list = b'', request: bool = False):
        head = request if LedPacketHead.REQUEST else LedPacketHead.COMMAND
        packet = LedPacket(head, cmd, payload)
        self._packet_buffer.append(packet)
        
    async def sendPacketBuffer(self):
        if len(self._packet_buffer) == 0:
            return None #nothing to do
        async with await self._getClient() as client:
            for packet in self._packet_buffer:
                frame = GoveeUtils.generateFrame(packet)
                await client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, frame, False)
            self._packet_buffer = []

    async def requestStateBuffered(self):
        await self._preparePacket(LedPacketCmd.POWER, request=True)

    async def requestBrightnessBuffered(self):
        await self._preparePacket(LedPacketCmd.BRIGHTNESS, request=True)

    async def requestColorBuffered(self):
        if self._segmented:
            await self._preparePacket(LedPacketCmd.SEGMENT, b'\x01', request=True) #0x01 means first segment
        else:
            await self._preparePacket(LedPacketCmd.COLOR, request=True)
    
    async def setStateBuffered(self, state: bool):
        await self._preparePacket(LedPacketCmd.POWER, [0x1 if state else 0x0])
    
    async def setBrightnessBuffered(self, value: int):
        if not 0 <= value <= 255:
            raise ValueError(f'Brightness out of range: {value}')
        value = round(value)
        if self._segmented:
            value = int(value / 255 * 100) #percentage
        await self._preparePacket(LedPacketCmd.BRIGHTNESS, [value])
        
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
        await self._preparePacket(LedPacketCmd.COLOR, payload)
