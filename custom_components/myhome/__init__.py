"""BTicino MyHOME integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN, PLATFORMS
from .coordinator import MyHOMEGatewayCoordinator

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up MyHOME gateway from a config entry."""
    
    coordinator = MyHOMEGatewayCoordinator(hass, entry.data)
    connected = await coordinator.async_connect()
    
    if not connected:
        raise ConfigEntryNotReady(
            f"Cannot connect to gateway {coordinator.mac} "
            f"at {coordinator.host}:{coordinator.port}"
        )
    
    entry.runtime_data = coordinator
    
    # Log subentries per debug
    _LOGGER.info(
        "Setting up gateway %s with %d subentries",
        entry.title,
        len(entry.subentries)
    )
    
    for subentry_id, subentry in entry.subentries.items():
        _LOGGER.debug(
            "Subentry %s: type=%s, data=%s",
            subentry_id,
            subentry.subentry_type,
            subentry.data
        )
    
    await coordinator.async_start_listener()
    
    # Setup platforms - questo caricherà le entity per ogni subentry
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = entry.runtime_data
    await coordinator.async_disconnect()
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)