import asyncio
import bleak_retry_connector
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak import (
    BleakClient,
    BLEDevice
)
from .const import WRITE_CHARACTERISTIC_UUID, READ_CHARACTERISTIC_UUID
from .api_utils import (
    LedPacketHead,
    LedPacketCmd,
    LedColorType,
    LedPacket,
    GoveeUtils
)

import logging
_LOGGER = logging.getLogger(__name__)

class GoveeAPI:
    def __init__(self, ble_device: BLEDevice, address: str, segmented: bool = False):
        self._conn = None
        self._ble_device = ble_device
        self._address = address
        self._segmented = segmented
        self._packet_buffer = []
        self._client = None
        self.state = None
        self.brightness  = None
        self.color = None

    async def _ensureConnected(self):
        """ connects to a bluetooth device """
        if self._client ==  None:
            self._client = await bleak_retry_connector.establish_connection(BleakClient, self._ble_device, self._address)

    async def disconnect(self):
        """ disconnects from a bluetooth device """
        if self._client !=  None:
            await self._client.disconnect()
            self._client = None

    async def _transmitPacket(self, packet: LedPacket):
        await self._ensureConnected()
        #convert to bytes
        frame = GoveeUtils.generateFrame(packet)
        #transmit to UUID
        await self._client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, frame, False)

    def _notification_handler(self, characteristic: BleakGATTCharacteristic, frame: bytearray):
        if not GoveeUtils.verifyChecksum(frame):
            _LOGGER.error("discard packet with bad checksum")
            self.stop_event.set() #checksum bad
            return None

        self.response_packet = LedPacket(
            head=hex(frame[0]),
            cmd=hex(frame[1]),
            payload=frame[2:-1]
        )
        self.stop_event.set()

    async def _sendPacketWithResponse(self, cmd: LedPacketCmd, payload: bytes | list = b''):
        await self._ensureConnected()
        self.response_packet = None
        self.stop_event = asyncio.Event()
        await self._client.start_notify(READ_CHARACTERISTIC_UUID, self._notification_handler)
        #transmit request
        packet = LedPacket(LedPacketHead.REQUEST, cmd, payload)
        await self._transmitPacket(packet)
        #wait for response
        await self.stop_event.wait()
        await self._client.stop_notify(READ_CHARACTERISTIC_UUID)
        return self.response_packet

    async def _preparePacket(self, cmd: LedPacketCmd, payload: bytes | list = b'', request: bool = False, repeat: int = 3):
        """ add data to transmission buffer """
        #request data or perform a change
        head = LedPacketHead.REQUEST if request else LedPacketHead.COMMAND
        packet = LedPacket(head, cmd, payload)
        for index in range(repeat):
            self._packet_buffer.append(packet)

    async def sendPacketBuffer(self):
        """ transmits all buffered data """
        if len(self._packet_buffer) == 0:
            #nothing to do
            return None
        for packet in self._packet_buffer:
            await self._transmitPacket(packet)
        #clear buffer
        self._packet_buffer = []

    async def requestState(self):
        """ adds a request for the current power state to the transmit buffer """
        packet = await self._sendPacketWithResponse(LedPacketCmd.POWER)
        assert packet
        self.state = packet.payload[0] == 0x01

    async def requestBrightness(self):
        """ adds a request for the current brightness state to the transmit buffer """
        packet = await self._sendPacketWithResponse(LedPacketCmd.BRIGHTNESS)
        assert packet
        if self._segmented:
            #segmented devices 0-100
            return packet.payload[0] / 100 * 255
        self.brightness = packet.payload[0]

    async def requestColor(self):
        """ adds a request for the current color state to the transmit buffer """
        if self._segmented:
            #0x01 means first segment
            packet = await self._sendPacketWithResponse(LedPacketCmd.SEGMENT, b'\x01')
            assert packet
            red = packet.payload[2]
            green = packet.payload[3]
            blue = packet.payload[4]
            self.color = (red, green, blue)
        else:
            #empty response on segmented devices
            packet = await self._sendPacketWithResponse(LedPacketCmd.COLOR)
            assert packet
            red = packet.payload[1]
            green = packet.payload[2]
            blue = packet.payload[3]
            self.color = (red, green, blue)
    
    async def setStateBuffered(self, state: bool):
        """ adds the state to the transmit buffer """
        if self.state == state:
            return None #nothing to do
        #0x1 = ON, Ox0 = OFF
        await self._preparePacket(LedPacketCmd.POWER, [0x1 if state else 0x0])
        self.state = state
    
    async def setBrightnessBuffered(self, brightness: int):
        """ adds the brightness to the transmit buffer """
        if self.brightness == brightness:
            return None #nothing to do
        #legacy devices 0-255
        payload = round(brightness)
        if self._segmented:
            #segmented devices 0-100
            payload = int(brightness / 255 * 100)
        await self._preparePacket(LedPacketCmd.BRIGHTNESS, [payload])
        self.brightness = brightness
        
    async def setColorBuffered(self, red: int, green: int, blue: int):
        """ adds the color to the transmit buffer """
        if self.color == (red, green, blue):
            return None #nothing to do
        #legacy devices
        payload = [LedColorType.SINGLE, red, green, blue]
        if self._segmented:
            payload = [LedColorType.SEGMENTS, 0x01, red, green, blue, 0, 0, 0, 0, 0, 0xff, 0xff]
        await self._preparePacket(LedPacketCmd.COLOR, payload)
        self.color = (red, green, blue)
