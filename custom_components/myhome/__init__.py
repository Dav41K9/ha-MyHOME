"""The BTicino MyHOME integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN, PLATFORMS
from .coordinator import MyHOMEGatewayCoordinator
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

type MyHOMEConfigEntry = ConfigEntry[MyHOMEGatewayCoordinator]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the MyHOME component (services only)."""
    await async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: MyHOMEConfigEntry) -> bool:
    """Set up MyHOME gateway from a config entry."""
    coordinator = MyHOMEGatewayCoordinator(hass, entry)

    connected = await coordinator.async_connect()
    if not connected:
        # Raise ConfigEntryNotReady so HA retries automatically
        raise ConfigEntryNotReady(
            f"Cannot connect to gateway {coordinator.mac} "
            f"at {coordinator.host}:{coordinator.port}"
        )

    entry.runtime_data = coordinator
    await coordinator.async_start_listener()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: MyHOMEConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = entry.runtime_data
        await coordinator.async_disconnect()
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: MyHOMEConfigEntry) -> None:
    """Handle removal of a config entry."""
    if not hass.config_entries.async_entries(DOMAIN):
        await async_unload_services(hass)


async def _async_update_listener(hass: HomeAssistant, entry: MyHOMEConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
