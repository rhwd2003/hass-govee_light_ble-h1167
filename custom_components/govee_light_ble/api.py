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
    def __init__(self, ble_device: BLEDevice, address: str, segmented: bool = False):
        self._conn = None
        self._ble_device = ble_device
        self._address = address
        self._segmented = segmented
        self._packet_buffer = []
        self._client = None

    async def _getClient(self):
        """ connects to bluetooth device """
        return await bleak_retry_connector.establish_connection(BleakClient, self._ble_device, self._address)

    async def _preparePacket(self, cmd: LedPacketCmd, payload: bytes | list = b'', request: bool = False):
        """ add data to transmission buffer """
        #request data or perform a change
        head = LedPacketHead.REQUEST if request else LedPacketHead.COMMAND
        packet = LedPacket(head, cmd, payload)
        self._packet_buffer.append(packet)

    async def sendPacketBuffer(self):
        """ transmits all buffered data """
        if len(self._packet_buffer) == 0:
            #nothing to do
            return None
        async with await self._getClient() as client:
            for packet in self._packet_buffer:
                #transmit to UUID
                await client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, frame, False)
            #clear buffer
            self._packet_buffer = []

    async def requestStateBuffered(self):
        """ adds a request for the current power state to the transmit buffer """
        await self._preparePacket(LedPacketCmd.POWER, request=True)

    async def requestBrightnessBuffered(self):
        """ adds a request for the current brightness state to the transmit buffer """
        await self._preparePacket(LedPacketCmd.BRIGHTNESS, request=True)

    async def requestColorBuffered(self):
        """ adds a request for the current color state to the transmit buffer """
        if self._segmented:
            #0x01 means first segment
            return await self._preparePacket(LedPacketCmd.SEGMENT, b'\x01', request=True)
        #empty response on segmented devices
        await self._preparePacket(LedPacketCmd.COLOR, request=True)
    
    async def setStateBuffered(self, state: bool):
        """ adds the state to the transmit buffer """
        #0x1 = ON, Ox0 = OFF
        await self._preparePacket(LedPacketCmd.POWER, [0x1 if state else 0x0])
    
    async def setBrightnessBuffered(self, brightness: int):
        """ adds the brightness to the transmit buffer """
        #legacy devices 0-255
        payload = round(brightness)
        if self._segmented:
            #segmented devices 0-100
            payload = int(brightness / 255 * 100)
        await self._preparePacket(LedPacketCmd.BRIGHTNESS, [payload])
        
    async def setColorBuffered(self, red: int, green: int, blue: int):
        """ adds the color to the transmit buffer """
        #legacy devices
        payload = [LedColorType.SINGLE, red, green, blue]
        if self._segmented:
            payload = [LedColorType.SEGMENTS, 0x01, red, green, blue, 0, 0, 0, 0, 0, 0xff, 0xff]
        await self._preparePacket(LedPacketCmd.COLOR, payload)
