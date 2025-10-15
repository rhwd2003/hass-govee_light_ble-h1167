from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.components.light import (ColorMode, LightEntity, ATTR_BRIGHTNESS, ATTR_RGB_COLOR, ATTR_EFFECT)
from homeassistant.const import CONF_ADDRESS, CONF_NAME
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import GoveeAPI
from .const import DOMAIN
from .coordinator import GoveeCoordinator
from .api_utils import EFFECT_MAP

import logging
_LOGGER = logging.getLogger(__name__)

def num_to_range(num, inMin, inMax, outMin, outMax):
    return outMin + (float(num - inMin) / float(inMax - inMin) * (outMax - outMin))

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up a Lights."""
    # This gets the data update coordinator from hass.data as specified in your __init__.py
    coordinator: GoveeCoordinator = hass.data[DOMAIN][
        config_entry.entry_id
    ].coordinator

    async_add_entities([
        GoveeBluetoothLight(coordinator)
    ], True)


class GoveeBluetoothLight(CoordinatorEntity, LightEntity):

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB

    def __init__(self, coordinator: GoveeCoordinator):
        """Initialize."""
        super().__init__(coordinator)
        self._attr_name = coordinator.device_name
        self._attr_unique_id = f"{coordinator.device_address}"
        
        # Set effect list based on device capabilities
        if coordinator.music_mode_support:
            self._attr_effect_list = list(EFFECT_MAP.keys())
        else:
            self._attr_effect_list = None
            
        self._attr_device_info = DeviceInfo(
            #only generate device once!
            manufacturer="GOVEE",
            model=coordinator.device_name,
            serial_number=coordinator.device_address,
            identifiers={(DOMAIN, coordinator.device_address)}
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()

    @property
    def brightness(self):
        """Return the current brightness. 1-255"""
        return self.coordinator.data.brightness

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self.coordinator.data.state

    @property
    def rgb_color(self) -> bool | None:
        """Return the current rgw color."""
        return self.coordinator.data.color
    
    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        return self.coordinator.data.current_effect

    async def async_turn_on(self, **kwargs):
        """Turn device on."""
        await self.coordinator.setStateBuffered(True)

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs.get(ATTR_BRIGHTNESS, 255) #1-255
            brightness_mapped = num_to_range(brightness, 1, 255, 0, 255) #mapping from 1-255 to 0-255
            await self.coordinator.setBrightnessBuffered(brightness_mapped)

        if ATTR_RGB_COLOR in kwargs:
            red, green, blue = kwargs.get(ATTR_RGB_COLOR)
            await self.coordinator.setColorBuffered(red, green, blue)

        if ATTR_EFFECT in kwargs and self.coordinator.music_mode_support:
            effect = kwargs.get(ATTR_EFFECT)
            if effect in EFFECT_MAP:
                await self.coordinator.setEffectBuffered(effect)
            else:
                _LOGGER.warning(f"Unknown effect: {effect}")
        
        await self.coordinator.sendPacketBuffer()

    
    async def async_turn_off(self, **kwargs):
        """Turn device off."""
        await self.coordinator.setStateBuffered(False)
        await self.coordinator.sendPacketBuffer()
