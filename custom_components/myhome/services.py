"""Services for the BTicino MyHOME integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SERVICE_SYNC_TIME = "sync_time"
SERVICE_SEND_MESSAGE = "send_message"
SERVICE_MIGRATE_YAML = "migrate_yaml"

ATTR_GATEWAY_MAC = "gateway_mac"
ATTR_MESSAGE = "message"

SYNC_TIME_SCHEMA = vol.Schema(
    {vol.Required(ATTR_GATEWAY_MAC): cv.string}
)

SEND_MESSAGE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_GATEWAY_MAC): cv.string,
        vol.Required(ATTR_MESSAGE): cv.string,
    }
)

MIGRATE_YAML_SCHEMA = vol.Schema({})


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register MyHOME services (once)."""
    if hass.services.has_service(DOMAIN, SERVICE_SYNC_TIME):
        return

    async def handle_sync_time(call: ServiceCall) -> None:
        mac = str(call.data[ATTR_GATEWAY_MAC])
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("mac") == mac and hasattr(entry, "runtime_data"):
                coordinator = entry.runtime_data
                await coordinator.async_send_message("*#13**1##")
                return

    async def handle_send_message(call: ServiceCall) -> None:
        mac = str(call.data[ATTR_GATEWAY_MAC])
        message = str(call.data[ATTR_MESSAGE])
        for entry in hass.config_entries.async_entries(DOMAIN):
            if entry.data.get("mac") == mac and hasattr(entry, "runtime_data"):
                coordinator = entry.runtime_data
                await coordinator.async_send_message(message)
                return

    async def handle_migrate_yaml(call: ServiceCall) -> None:
        from .migrate_yaml import async_migrate_yaml_to_subentries

        result = await async_migrate_yaml_to_subentries(hass)
        _LOGGER.info("MyHOME YAML migration result:\n%s", result)

    hass.services.async_register(
        DOMAIN, SERVICE_SYNC_TIME, handle_sync_time, schema=SYNC_TIME_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SEND_MESSAGE, handle_send_message, schema=SEND_MESSAGE_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_MIGRATE_YAML, handle_migrate_yaml, schema=MIGRATE_YAML_SCHEMA
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unregister MyHOME services."""
    hass.services.async_remove(DOMAIN, SERVICE_SYNC_TIME)
    hass.services.async_remove(DOMAIN, SERVICE_SEND_MESSAGE)
    hass.services.async_remove(DOMAIN, SERVICE_MIGRATE_YAML)
