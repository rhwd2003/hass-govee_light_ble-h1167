from dataclasses import dataclass
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.components import bluetooth

from .const import DOMAIN
from .api import GoveeAPI

import logging
_LOGGER = logging.getLogger(__name__)

@dataclass
class GoveeApiData:
    """Class to hold api data."""

    state: bool | None = None
    brightness: int | None = None
    color: tuple[int, ...] | None = None
    current_effect: str | None = None
    music_mode_enabled: bool = False

class GoveeCoordinator(DataUpdateCoordinator):
    """My coordinator."""

    data: GoveeApiData

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""

        # Set variables from values entered in config flow setup
        self.device_name = config_entry.data[CONF_NAME]
        self.device_address = config_entry.data[CONF_ADDRESS]
        self.device_segmented = config_entry.data["segmented"]
        self.is_h1167 = config_entry.data.get("is_h1167", False)
        self.music_mode_support = config_entry.data.get("music_mode_support", False)

        # Get connection to bluetooth device
        # Note: connectable should be True for devices we want to connect to
        ble_device = bluetooth.async_ble_device_from_address(
            hass,
            self.device_address,
            connectable=True  # Changed from False to True for proper connection
        )
        
        if not ble_device:
            _LOGGER.error(f"Could not find BLE device with address {self.device_address}")
            raise ValueError(f"BLE device {self.device_address} not found")
            
        _LOGGER.info(f"Initializing Govee device: {self.device_name} ({self.device_address})")
        self._api = GoveeAPI(ble_device, self._async_push_data, self.device_segmented)

        # Initialise DataUpdateCoordinator
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN} ({config_entry.unique_id})",
            # Set update method to get devices on first load.
            update_method=self._async_update_data,
            # Do not set a polling interval as data will be pushed.
            # You can remove this line but left here for explanatory purposes.
            update_interval=timedelta(seconds=15)
        )

    def _get_data(self):
        return GoveeApiData(
            state=self._api.state,
            brightness=self._api.brightness,
            color=self._api.color,
            current_effect=self._api.current_effect,
            music_mode_enabled=self._api.music_mode_enabled
        )

    async def _async_push_data(self):
        self.async_set_updated_data(self._get_data())

    async def _async_update_data(self):
        """Fetch data from API endpoint with improved error handling.

        This is the place to pre-process the data to lookup tables
        so entities can quickly look up their data.
        """
        try:
            await self._api.requestStateBuffered()
            await self._api.requestBrightnessBuffered()
            await self._api.requestColorBuffered()
            
            # Only request music mode for devices that support it
            if self.music_mode_support:
                await self._api.requestMusicModeBuffered()
                
            await self._api.sendPacketBuffer()
            
            # Log successful update if we had previous failures
            if self._api.connection_failures > 0:
                _LOGGER.info(f"Successfully updated {self.device_name} after previous connection issues")
                
            return self._get_data()
            
        except Exception as e:
            _LOGGER.warning(
                f"Failed to update {self.device_name} ({self.device_address}): {type(e).__name__}: {e}. "
                f"Connection failures: {self._api.connection_failures}"
            )
            # Return last known data instead of raising exception
            # This prevents the device from becoming unavailable on temporary connection issues
            return self._get_data()

    async def setStateBuffered(self, state: bool):
        await self._api.setStateBuffered(state)

    async def setBrightnessBuffered(self, brightness: int):
        await self._api.setBrightnessBuffered(brightness)

    async def setColorBuffered(self, red: int, green: int, blue: int):
        await self._api.setColorBuffered(red, green, blue)

    async def sendPacketBuffer(self):
        await self._api.sendPacketBuffer()
    
    async def setEffectBuffered(self, effect_name: str):
        await self._api.setEffectBuffered(effect_name)
    
    async def setMusicModeBuffered(self, enabled: bool):
        await self._api.setMusicModeBuffered(enabled)
    
    async def reset_connection(self):
        """Reset the connection to the device."""
        await self._api.reset_connection_state()
        _LOGGER.info(f"Reset connection for {self.device_name}")
    
    @property
    def connection_status(self):
        """Get connection status information."""
        return {
            "is_connected": self._api.is_connected,
            "connection_failures": self._api.connection_failures,
            "address": self.device_address,
            "name": self.device_name
        }
