from __future__ import annotations

from enum import IntEnum
from dataclasses import dataclass
from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import CONF_ADDRESS, CONF_NAME

from .const import DOMAIN
import logging
_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT]

class BlePacket(IntEnum):
    STATUS = 34819

@dataclass
class RuntimeData:
    """Class to hold your data."""

    device_address: str
    device_name: str
    device_segmented: str
    device_state: bool | None

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up Integration from a config entry."""

    hass.data.setdefault(DOMAIN, {})

    device_address = config_entry.data[CONF_ADDRESS]
    device_name = config_entry.data[CONF_NAME]
    device_segmented = config_entry.data["segmented"]

    #look for device
    if not bluetooth.async_ble_device_from_address(hass, device_address, True):
        raise ConfigEntryNotReady(
            f"Could not find LED BLE device with address {address}"
        )
    
    #get device status
    service_info = bluetooth.async_last_service_info(hass, device_address, connectable=False)
    device_state = None
    if BlePacket.STATUS in service_info.manufacturer_data:
        device_state = service_info.manufacturer_data[BlePacket.STATUS][4] == 1

    # Add the coordinator and update listener to hass data to make
    hass.data[DOMAIN][config_entry.entry_id] = RuntimeData(
        device_address = device_address,
        device_name = device_name,
        device_segmented = device_segmented,
        device_state = device_state
    )

    # Setup platforms (based on the list of entity types in PLATFORMS defined above)
    # This calls the async_setup method in each of your entity type files.
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    # Return true to denote a successful setup.
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # This is called when you remove your integration or shutdown HA.
    # If you have created any custom services, they need to be removed here too.

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
