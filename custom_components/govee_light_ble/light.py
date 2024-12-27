from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components import bluetooth
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.components.light import (ColorMode, LightEntity, ATTR_BRIGHTNESS, ATTR_RGB_COLOR)

from .api import GoveeAPI
from .const import DOMAIN

import logging
_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up a Buttons."""
    # This gets the data update coordinator from hass.data as specified in your __init__.py
    runtime_data = hass.data[DOMAIN][config_entry.entry_id]
    ble_device = bluetooth.async_ble_device_from_address(
        hass,
        runtime_data.device_address,
        connectable=False
    )
    api = GoveeAPI(ble_device, runtime_data.device_address, runtime_data.device_segmented)
    #request current values from device
    await api.requestStateBuffered()
    await api.requestBrightnessBuffered()
    await api.requestColorBuffered()
    await api.sendPacketBuffer()

    async_add_entities([
        GoveeBluetoothLight(
            device_address=runtime_data.device_address,
            device_name=runtime_data.device_name,
            api=api
        )
    ], True)


class GoveeBluetoothLight(LightEntity):

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB

    def __init__(self, device_address: str, device_name: str, api: GoveeAPI):
        """Initialize."""
        self._attr_name = device_name
        self._attr_unique_id = f"{device_address}"
        self._attr_device_info = DeviceInfo(
            #only generate device once!
            manufacturer="GOVEE",
            model=device_name,
            serial_number=device_address,
            identifiers={(DOMAIN, device_address)}
        )
        self._api = api

    @property
    def brightness(self):
        """Return the current brightness."""
        return self._api.brightness

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._api.state

    @property
    def rgb_color(self) -> bool | None:
        """Return the current rgw color."""
        return self._api.color

    async def async_turn_on(self, **kwargs):
        """Turn device on."""
        await self._api.setStateBuffered(True)

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
            await self._api.setBrightnessBuffered(brightness)

        if ATTR_RGB_COLOR in kwargs:
            red, green, blue = kwargs.get(ATTR_RGB_COLOR)
            await self._api.setColorBuffered(red, green, blue)
        
        await self._api.sendPacketBuffer()

    
    async def async_turn_off(self, **kwargs):
        """Turn device off."""
        await self._api.setStateBuffered(False)
        await self._api.sendPacketBuffer()
