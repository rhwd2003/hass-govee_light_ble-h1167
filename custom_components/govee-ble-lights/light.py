from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.device_registry import DeviceInfo

from homeassistant.components import bluetooth
from homeassistant.components.light import (ColorMode, LightEntity, ATTR_BRIGHTNESS, ATTR_RGB_COLOR)

from .bluetooth_led import BluetoothLED

from .const import DOMAIN

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    """Set up a Buttons."""
    # This gets the data update coordinator from hass.data as specified in your __init__.py
    address: str = hass.data[DOMAIN][
        config_entry.entry_id
    ].address


    ble_device = await bluetooth.async_ble_device_from_address(hass, address, connectable=False)
    async_add_entities([
        GoveeBluetoothLight(address, ble_device)
    ], True)


class GoveeBluetoothLight(LightEntity):

    _attr_has_entity_name = True
    _attr_translation_key = "goveeblelight"
    _attr_supported_color_modes = {ColorMode.ONOFF, ColorMode.BRIGHTNESS, ColorMode.RGB}
    _attr_color_mode = ColorMode.RGB

    def __init__(self, address: str, ble_device):
        """Initialize."""
        self.unique_id = f"{address}"
        self.device_info = DeviceInfo(
            #only generate device once!
            manufacturer="GOVEE",
            identifiers={(DOMAIN, address)}
        )
        self._address = address
        self._api = BluetoothLED(ble_device)
        self._brightness = None
        self._state = None
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
        await self._api.connect(self._address)

        if ATTR_BRIGHTNESS in kwargs:
            brightness = kwargs.get(ATTR_BRIGHTNESS, 255)
            await self._api.set_brightness(brightness)
            self._brightness = brightness

        if ATTR_RGB_COLOR in kwargs:
            red, green, blue = kwargs.get(ATTR_RGB_COLOR)
            await self._api.set_color(red, green, blue)
            self._rgb = (red, green, blue)

        await self._api.disconnect()
        self._state = True

    
    async def async_turn_off(self, **kwargs):
        """Turn device off."""
        await self._api.connect(self._address)
        await self._api.set_state(False)
        await self._api.disconnect()
        self._state = False