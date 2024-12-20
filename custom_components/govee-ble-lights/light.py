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
    device_address = hass.data[DOMAIN][config_entry.entry_id].device_address
    device_name = hass.data[DOMAIN][config_entry.entry_id].device_name
    device_segmented = hass.data[DOMAIN][config_entry.entry_id].device_segmented
    device_state = hass.data[DOMAIN][config_entry.entry_id].device_state

    ble_device = bluetooth.async_ble_device_from_address(hass, device_address, True)
    async_add_entities([
        GoveeBluetoothLight(device_address, device_name, device_state, device_segmented, ble_device)
    ], True)


class GoveeBluetoothLight(LightEntity):

    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB

    def __init__(self, address: str, name: str, state: bool, segmented: bool, ble_device):
        """Initialize."""
        self._attr_name = name
        self._attr_unique_id = f"{address}"
        self._attr_device_info = DeviceInfo(
            #only generate device once!
            manufacturer="GOVEE",
            identifiers={(DOMAIN, address)}
        )
        self._segmented = segmented
        self._address = address
        self._api = GoveeAPI(ble_device)
        self._brightness = None
        self._state = state
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

    async def _setState(self, state: bool):
        if self._state is state:
            return None
        await self._api.set_state(state)
        self._state = state

    async def _setBrightness(self, brightness: int):
        if self._brightness is brightness:
            return None
        await self._api.set_brightness(brightness)
        self._brightness = brightness

    async def _setColor(self, red: int, green: int, blue: int):
        if self._rgb is (red, green, blue):
            return None
        await self._api.set_color(red, green, blue, self._segmented)
        self._rgb = (red, green, blue)

    async def async_turn_on(self, **kwargs):
        """Turn device on."""
        await self._api.connect(self._address)
        await self._setState(True)

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
            await self._setBrightness(brightness)

        if ATTR_RGB_COLOR in kwargs:
            red, green, blue = kwargs.get(ATTR_RGB_COLOR)
            await self._setColor(red, green, blue)

        await self._api.disconnect()

    
    async def async_turn_off(self, **kwargs):
        """Turn device off."""
        await self._api.connect(self._address)
        await self._setState(False)
        await self._api.disconnect()
