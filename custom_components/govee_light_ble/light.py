from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.components import bluetooth
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.components.light import (ColorMode, LightEntity, ATTR_BRIGHTNESS, ATTR_RGB_COLOR)

from .api import GoveeAPI
from .const import DOMAIN

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
    async_add_entities([
        GoveeBluetoothLight(
            device_address=runtime_data.device_address,
            device_name=runtime_data.device_name,
            device_state=runtime_data.device_state,
            device_segmented=runtime_data.device_segmented,
            ble_device=ble_device
        )
    ], True)


class GoveeBluetoothLight(LightEntity):

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB

    def __init__(self, device_address: str, device_name: str, device_state: bool, device_segmented: bool, ble_device):
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
        self._api = GoveeAPI(ble_device, device_address, device_segmented)
        self._brightness = None
        self._state = device_state
        self._rgb = None

    @property
    def brightness(self):
        """Return the current brightness."""
        return self._brightness

    @property
    def is_on(self) -> bool | None:
        """Return true if light is on."""
        return self._state

    @property
    def rgb_color(self) -> bool | None:
        """Return the current rgw color."""
        return self._rgb

    async def async_turn_on(self, **kwargs):
        """Turn device on."""
        state = True
        if self._state != state:
            self._state = state
            await self._api.setStateBuffered(state)

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
            if self._brightness != brightness:
                self._brightness = brightness
                await self._api.setBrightnessBuffered(brightness)

        if ATTR_RGB_COLOR in kwargs:
            red, green, blue = kwargs.get(ATTR_RGB_COLOR)
            if self._rgb != (red, green, blue):
                self._rgb = (red, green, blue)
                await self._api.setColorBuffered(red, green, blue)
        
        await self._api.sendPacketBuffer()

    
    async def async_turn_off(self, **kwargs):
        """Turn device off."""
        state = False
        if self._state != state:
            self._state = state
            await self._api.setStateBuffered(state)
        await self._api.sendPacketBuffer()
