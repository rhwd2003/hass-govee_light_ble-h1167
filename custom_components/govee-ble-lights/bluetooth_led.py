from enum import IntEnum
from colour import Color
from .const import values as SHADES_OF_WHITE

UUID_CONTROL_CHARACTERISTIC = '00010203-0405-0607-0809-0a0b0c0d2b11'

class LedCommand(IntEnum):
    POWER      = 0x01
    BRIGHTNESS = 0x04
    COLOR      = 0x05

class LedMode(IntEnum):
    MANUAL     = 0x02
    MICROPHONE = 0x06
    SCENES     = 0x05

class BluetoothLED:
    def __init__(self):
        self._conn = None
    
    async def connect(self, address: str):
        self._conn = await self._bt.connect(address)

    async def disconnect(self):
        if self._conn is None:
            await self._conn.disconnect()

    async def _send(self, cmd, payload):
        if self._conn is None:
            raise Exception('not connected to bluetooth device')
        if not isinstance(cmd, int):
           raise ValueError('Invalid command')
        if not isinstance(payload, bytes) and not (isinstance(payload, list) and all(isinstance(x, int) for x in payload)):
            raise ValueError('Invalid payload')
        if len(payload) > 17:
            raise ValueError('Payload too long')

        cmd = cmd & 0xFF
        payload = bytes(payload)

        frame = bytes([0x33, cmd]) + bytes(payload)
        # pad frame data to 19 bytes (plus checksum)
        frame += bytes([0] * (19 - len(frame)))
        
        # The checksum is calculated by XORing all data bytes
        checksum = 0
        for b in frame:
            checksum ^= b
        
        frame += bytes([checksum & 0xFF])
        await self._conn.char_write(UUID_CONTROL_CHARACTERISTIC, frame)
    
    async def set_state(self, state: bool):
        self._send(LedCommand.POWER, [0x1 if state else 0x0])
    
    async def set_brightness(self, value: int):
        if not 0 <= value <= 255:
            raise ValueError(f'Brightness out of range: {value}')
        value = round(value)
        await self._send(LedCommand.BRIGHTNESS, [value])
        
    async def set_color(self, red: int, green: int, blue: int):
        await self._send(LedCommand.COLOR, [LedMode.MANUAL, red, green, blue])