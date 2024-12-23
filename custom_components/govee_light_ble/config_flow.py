from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_ADDRESS, CONF_NAME, CONF_TYPE
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import selector

from .const import DOMAIN, DISCOVERY_NAMES


class GoveeConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovery_info: None = None
        self._discovered_device: None = None
        self._discovered_devices: dict[str, str] = {}

    #dicover device
    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> FlowResult:
        """Handle the bluetooth discovery step."""
        self._discovery_info = discovery_info
        return await self.async_step_bluetooth_confirm()

    #manual integration
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the user step to pick discovered device."""
        if user_input is not None:
            address = user_input[CONF_ADDRESS]
            self._discovery_info = self._discovered_devices[address]
            return await self.async_step_bluetooth_confirm()

        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(self.hass, False):
            address = discovery_info.address
            if address in current_addresses or address in self._discovered_devices:
                continue
            if not discovery_info.name.startswith(DISCOVERY_NAMES):
                continue
            self._discovered_devices[address] = discovery_info

        if not self._discovered_devices:
            return self.async_abort(reason="no_devices_found")

        device_list = {}
        for address in self._discovered_devices:
            device_list[address] = self._discovered_devices[address].name
    
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(device_list)}
            ),
        )

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Confirm discovery."""
        assert self._discovery_info is not None
        discovery_info = self._discovery_info
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title=discovery_info.name, data={
                CONF_ADDRESS: discovery_info.address.upper(),
                CONF_NAME: discovery_info.name,
                "segmented": user_input["segmented"]
            })

        return self.async_show_form(
            step_id="bluetooth_confirm", data_schema=vol.Schema({
                vol.Required("segmented", default=True): bool
            }))
