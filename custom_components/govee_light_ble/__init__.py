from __future__ import annotations

from typing import Callable
from enum import IntEnum
from dataclasses import dataclass
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import CONF_ADDRESS
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .coordinator import GoveeCoordinator
from .const import DOMAIN

import logging
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT]

@dataclass
class RuntimeData:
    """Class to hold your data."""

    coordinator: GoveeCoordinator
    cancel_update_listener: Callable

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Integration from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    # Look for device
    device_address = config_entry.data[CONF_ADDRESS]
    ble_device = bluetooth.async_ble_device_from_address(hass, device_address, True)
    
    if not ble_device:
        _LOGGER.warning(f"Could not find LED BLE device with address {device_address}, will retry")
        raise ConfigEntryNotReady(
            f"Could not find LED BLE device with address {device_address}"
        )

    _LOGGER.info(f"Setting up Govee Light BLE integration for {config_entry.data.get('name', device_address)}")

    # Initialise the coordinator that manages data updates from your api.
    # This is defined in coordinator.py
    try:
        coordinator = GoveeCoordinator(hass, config_entry)
    except Exception as e:
        _LOGGER.error(f"Failed to initialize coordinator for {device_address}: {e}")
        raise ConfigEntryNotReady(f"Failed to initialize coordinator: {e}")

    # Perform an initial data load from api.
    # async_config_entry_first_refresh() is special in that it does not log errors if it fails
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as e:
        _LOGGER.warning(f"Initial refresh failed for {device_address}, will continue anyway: {e}")

    # Initialise a listener for config flow options changes.
    # See config_flow for defining an options setting that shows up as configure on the integration.
    cancel_update_listener = config_entry.add_update_listener(_async_update_listener)

    # Add the coordinator and update listener to hass data to make
    hass.data[DOMAIN][config_entry.entry_id] = RuntimeData(
        coordinator, cancel_update_listener
    )

    # Setup platforms (based on the list of entity types in PLATFORMS defined above)
    # This calls the async_setup method in each of your entity type files.
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Return true to denote a successful setup.
    return True

async def _async_update_listener(hass: HomeAssistant, config_entry):
    """Handle config options update."""
    # Reload the integration when the options change.
    await hass.config_entries.async_reload(config_entry.entry_id)

async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when you remove your integration or shutdown HA.
    # If you have created any custom services, they need to be removed here too.

    _LOGGER.info(f"Unloading Govee Light BLE integration for {config_entry.data.get('name', config_entry.data[CONF_ADDRESS])}")

    # Get the runtime data
    runtime_data = hass.data[DOMAIN].get(config_entry.entry_id)
    
    if runtime_data:
        # Remove the config options update listener
        runtime_data.cancel_update_listener()
        
        # Disconnect from the device
        try:
            coordinator = runtime_data.coordinator
            await coordinator.reset_connection()
            _LOGGER.debug(f"Successfully disconnected from {coordinator.device_address}")
        except Exception as e:
            _LOGGER.warning(f"Error disconnecting during unload: {e}")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    # Remove the config entry from the hass data object.
    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    # Return that unloading was successful.
    return unload_ok

async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
    """Migrate old entry."""
    _LOGGER.debug("Migrating configuration from version %s", config_entry.version)

    if config_entry.version == 1:
        hass.config_entries.async_update_entry(config_entry, data={
            CONF_ADDRESS: config_entry.unique_id.upper(),
            CONF_NAME: config_entry.title,
            "segmented": True
        }, version=2)

    _LOGGER.debug("Migration to configuration version %s successful", config_entry.version)

    return True
