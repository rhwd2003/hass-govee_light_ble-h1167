import asyncio
import time
import bleak_retry_connector
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak import (
    BleakClient,
    BLEDevice
)
from bleak_retry_connector import BleakOutOfConnectionSlotsError
from .const import (
    WRITE_CHARACTERISTIC_UUID, 
    READ_CHARACTERISTIC_UUID,
    MAX_CONNECTION_ATTEMPTS,
    CONNECTION_TIMEOUT,
    RETRY_DELAY,
    INITIAL_CONNECTION_TIMEOUT,
    RECONNECTION_TIMEOUT
)
from .api_utils import (
    LedPacketHead,
    LedPacketCmd,
    LedColorType,
    LedPacket,
    GoveeUtils,
    MusicModeType,
    CarnivalModeType,
    BasicModeType,
    EFFECT_MAP
)

import logging
_LOGGER = logging.getLogger(__name__)

class GoveeAPI:
    state: bool | None = None
    brightness: int | None = None
    color: tuple[int, ...] | None = None
    current_effect: str | None = None
    music_mode_enabled: bool = False

    def __init__(self, ble_device: BLEDevice, update_callback, segmented: bool = False):
        self._conn = None
        self._ble_device = ble_device
        self._segmented = segmented
        self._packet_buffer = []
        self._client = None
        self._update_callback = update_callback
        self._connection_lock = asyncio.Lock()
        self._last_connection_attempt = 0
        self._connection_failures = 0

    @property
    def address(self):
        return self._ble_device.address

    async def _ensureConnected(self):
        """Ensures a connection to the bluetooth device with proper locking."""
        async with self._connection_lock:
            if self._client and self._client.is_connected:
                return
            await self._connect()
    
    async def _connect(self):
        """Connect to the BLE device with improved error handling and retry logic."""
        current_time = time.time()
        
        # Implement exponential backoff for repeated failures
        if self._connection_failures > 0:
            backoff_delay = min(2 ** self._connection_failures, 30)  # Max 30 seconds
            if current_time - self._last_connection_attempt < backoff_delay:
                _LOGGER.debug(f"Skipping connection attempt for {self.address} due to backoff (failures: {self._connection_failures})")
                raise Exception(f"Connection backoff active for {self.address}")
        
        self._last_connection_attempt = current_time
        last_exception = None
        
        # Clean up any existing connection first
        await self._cleanup_connection()
        
        for attempt in range(MAX_CONNECTION_ATTEMPTS):
            try:
                _LOGGER.info(f"Connection attempt {attempt + 1}/{MAX_CONNECTION_ATTEMPTS} for {self.address}")
                
                # Determine timeout based on whether this is initial connection or reconnection
                timeout = INITIAL_CONNECTION_TIMEOUT if self._connection_failures == 0 else RECONNECTION_TIMEOUT
                
                # Create a fresh BleakClient for each attempt
                self._client = BleakClient(self._ble_device)
                
                # Connect with timeout
                await asyncio.wait_for(
                    self._client.connect(),
                    timeout=timeout
                )
                
                if not self._client.is_connected:
                    raise Exception("Connection established but client reports not connected")
                
                # Start notifications
                await self._client.start_notify(READ_CHARACTERISTIC_UUID, self._handleReceive)
                
                # Reset failure counter on successful connection
                self._connection_failures = 0
                _LOGGER.info(f"Successfully connected to {self.address} on attempt {attempt + 1}")
                return
                
            except BleakOutOfConnectionSlotsError as e:
                last_exception = e
                _LOGGER.warning(f"Connection slot error for {self.address}, attempt {attempt + 1}: {e}")
                await self._cleanup_connection()
                if attempt < MAX_CONNECTION_ATTEMPTS - 1:
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))  # Exponential backoff
                    
            except asyncio.TimeoutError as e:
                last_exception = e
                _LOGGER.warning(f"Connection timeout for {self.address}, attempt {attempt + 1} (timeout: {timeout}s)")
                await self._cleanup_connection()
                if attempt < MAX_CONNECTION_ATTEMPTS - 1:
                    await asyncio.sleep(RETRY_DELAY)
                    
            except Exception as e:
                last_exception = e
                _LOGGER.warning(f"Connection error for {self.address}, attempt {attempt + 1}: {type(e).__name__}: {e}")
                await self._cleanup_connection()
                if attempt < MAX_CONNECTION_ATTEMPTS - 1:
                    await asyncio.sleep(RETRY_DELAY)
        
        # All attempts failed, increment failure counter
        self._connection_failures += 1
        error_msg = f"Failed to connect to {self.address} after {MAX_CONNECTION_ATTEMPTS} attempts (failure count: {self._connection_failures})"
        _LOGGER.error(error_msg)
        raise last_exception or Exception(error_msg)
    
    async def _cleanup_connection(self):
        """Clean up any existing connection state."""
        if self._client:
            try:
                if self._client.is_connected:
                    await self._client.disconnect()
            except Exception as e:
                _LOGGER.debug(f"Error during connection cleanup for {self.address}: {e}")
            finally:
                self._client = None
    
    async def _disconnect(self):
        """Properly disconnect from the BLE device."""
        async with self._connection_lock:
            if self._client and self._client.is_connected:
                try:
                    await self._client.stop_notify(READ_CHARACTERISTIC_UUID)
                    await self._client.disconnect()
                    _LOGGER.debug(f"Disconnected from {self.address}")
                except Exception as e:
                    _LOGGER.warning(f"Error disconnecting from {self.address}: {e}")
                finally:
                    self._client = None

    async def _transmitPacket(self, packet: LedPacket):
        """ transmit the actiual packet """
        #convert to bytes
        frame = await GoveeUtils.generateFrame(packet)
        #transmit to UUID
        await self._client.write_gatt_char(WRITE_CHARACTERISTIC_UUID, frame, False)

    async def _handleRequest(self, packet: LedPacket):
        """ process received responses """
        match packet.cmd:
            case LedPacketCmd.POWER:
                self.state = packet.payload[0] == 0x01
            case LedPacketCmd.BRIGHTNESS:
                #segmented devices 0-100
                self.brightness = packet.payload[0] / 100 * 255 if self._segmented else packet.payload[0]
            case LedPacketCmd.COLOR:
                red = packet.payload[1]
                green = packet.payload[2]
                blue = packet.payload[3]
                self.color = (red, green, blue)
            case LedPacketCmd.SEGMENT:
                red = packet.payload[2]
                green = packet.payload[3]
                blue = packet.payload[4]
                self.color = (red, green, blue)
            case LedPacketCmd.MUSIC_MODE:
                if len(packet.payload) > 0:
                    mode_value = packet.payload[0]
                    self.music_mode_enabled = mode_value != 0x00
                    # Find the effect name from the mode value
                    for effect_name, effect_value in EFFECT_MAP.items():
                        if effect_value == mode_value:
                            self.current_effect = effect_name
                            break
                    else:
                        self.current_effect = None if mode_value == 0x00 else f"Unknown_{mode_value:02x}"
            case LedPacketCmd.EFFECT | LedPacketCmd.SCENE:
                if len(packet.payload) > 0:
                    mode_value = packet.payload[0]
                    # Find the effect name from the mode value
                    for effect_name, effect_value in EFFECT_MAP.items():
                        if effect_value == mode_value:
                            self.current_effect = effect_name
                            break
                    else:
                        self.current_effect = f"Unknown_{mode_value:02x}" if mode_value != 0x00 else None

    async def _handleReceive(self, characteristic: BleakGATTCharacteristic, frame: bytearray):
        """ receives packets async """
        if not await GoveeUtils.verifyChecksum(frame):
            raise Exception("transmission error, received packet with bad checksum")
        
        packet = LedPacket(
            head=frame[0],
            cmd=frame[1],
            payload=frame[2:-1]
        )
        #only requests are expected to send a response
        if packet.head == LedPacketHead.REQUEST:
            await self._handleRequest(packet)
            await self._update_callback()

    async def _preparePacket(self, cmd: LedPacketCmd, payload: bytes | list = b'', request: bool = False, repeat: int = 3):
        """ add data to transmission buffer """
        #request data or perform a change
        head = LedPacketHead.REQUEST if request else LedPacketHead.COMMAND
        packet = LedPacket(head, cmd, payload)
        for index in range(repeat):
            self._packet_buffer.append(packet)

    async def _clearPacketBuffer(self):
        """ clears the packet buffer """
        self._packet_buffer = []

    async def sendPacketBuffer(self):
        """Transmits all buffered data with improved error handling."""
        if not self._packet_buffer:
            # Nothing to do
            return None
            
        try:
            await self._ensureConnected()
            
            # Send all packets
            for i, packet in enumerate(self._packet_buffer):
                try:
                    await self._transmitPacket(packet)
                    # Small delay between packets to avoid overwhelming the device
                    if i < len(self._packet_buffer) - 1:
                        await asyncio.sleep(0.05)  # 50ms delay
                except Exception as e:
                    _LOGGER.warning(f"Failed to transmit packet {i+1}/{len(self._packet_buffer)} to {self.address}: {e}")
                    # Don't break the loop, try to send remaining packets
                    
            await self._clearPacketBuffer()
            _LOGGER.debug(f"Successfully sent packet buffer to {self.address}")
            
        except Exception as e:
            _LOGGER.error(f"Failed to send packet buffer to {self.address}: {e}")
            # Clear buffer even on failure to prevent infinite retries
            await self._clearPacketBuffer()
            raise

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
            await self._preparePacket(LedPacketCmd.SEGMENT, b'\x01', request=True)
        else:
            #legacy devices
            await self._preparePacket(LedPacketCmd.COLOR, request=True)
    
    async def requestMusicModeBuffered(self):
        """ adds a request for the current music mode state to the transmit buffer """
        await self._preparePacket(LedPacketCmd.MUSIC_MODE, request=True)
    
    async def setStateBuffered(self, state: bool):
        """ adds the state to the transmit buffer """
        if self.state == state:
            return None #nothing to do
        #0x1 = ON, Ox0 = OFF
        await self._preparePacket(LedPacketCmd.POWER, [0x1 if state else 0x0])
        await self.requestStateBuffered()
    
    async def setBrightnessBuffered(self, brightness: int):
        """ adds the brightness to the transmit buffer """
        if self.brightness == brightness:
            return None #nothing to do
        #legacy devices 0-255
        payload = round(brightness)
        if self._segmented:
            #segmented devices 0-100
            payload = round(brightness / 255 * 100)
        await self._preparePacket(LedPacketCmd.BRIGHTNESS, [payload])
        await self.requestBrightnessBuffered()
        
    async def setColorBuffered(self, red: int, green: int, blue: int):
        """ adds the color to the transmit buffer """
        if self.color == (red, green, blue):
            return None #nothing to do
        if self._segmented:
            await self._preparePacket(LedPacketCmd.COLOR, [LedColorType.SEGMENTS, 0x01, red, green, blue, 0, 0, 0, 0, 0, 0xff, 0xff])
        else:
            #legacy devices
            await self._preparePacket(LedPacketCmd.COLOR, [LedColorType.SINGLE, red, green, blue])
            await self._preparePacket(LedPacketCmd.COLOR, [LedColorType.LEGACY, red, green, blue])
        await self.requestColorBuffered()
    
    async def setEffectBuffered(self, effect_name: str):
        """ adds the effect/music mode to the transmit buffer """
        if effect_name not in EFFECT_MAP:
            _LOGGER.warning(f"Unknown effect: {effect_name}")
            return None
            
        if self.current_effect == effect_name:
            return None  # nothing to do
            
        effect_value = EFFECT_MAP[effect_name]
        
        # Determine which command to use based on effect type
        if isinstance(effect_value, MusicModeType):
            await self._preparePacket(LedPacketCmd.MUSIC_MODE, [effect_value])
        elif isinstance(effect_value, (CarnivalModeType, BasicModeType)):
            await self._preparePacket(LedPacketCmd.EFFECT, [effect_value])
        
        await self.requestMusicModeBuffered()
    
    async def reset_connection_state(self):
        """Reset connection state and failure counters."""
        async with self._connection_lock:
            self._connection_failures = 0
            self._last_connection_attempt = 0
            await self._cleanup_connection()
            _LOGGER.info(f"Reset connection state for {self.address}")
    
    @property
    def connection_failures(self):
        """Get the current number of connection failures."""
        return self._connection_failures
    
    @property
    def is_connected(self):
        """Check if the device is currently connected."""
        return self._client and self._client.is_connected
    
    async def setMusicModeBuffered(self, enabled: bool):
        """ enables or disables music mode """
        if self.music_mode_enabled == enabled:
            return None  # nothing to do
            
        if enabled:
            # Default to Rhythm mode when enabling
            await self._preparePacket(LedPacketCmd.MUSIC_MODE, [MusicModeType.RHYTHM])
        else:
            # Turn off music mode
            await self._preparePacket(LedPacketCmd.MUSIC_MODE, [MusicModeType.OFF])
        
        await self.requestMusicModeBuffered()
    
    async def reset_connection_state(self):
        """Reset connection state and failure counters."""
        async with self._connection_lock:
            self._connection_failures = 0
            self._last_connection_attempt = 0
            await self._cleanup_connection()
            _LOGGER.info(f"Reset connection state for {self.address}")
    
    @property
    def connection_failures(self):
        """Get the current number of connection failures."""
        return self._connection_failures
    
    @property
    def is_connected(self):
        """Check if the device is currently connected."""
        return self._client and self._client.is_connected
