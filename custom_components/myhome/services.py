"""Domain services: sync_time, send_message, import_yaml."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from OWNd.message import OWNGatewayCommand

from .const import (
    DOMAIN,
    LOGGER,
    SERVICE_IMPORT_YAML,
    SERVICE_SEND_MESSAGE,
    SERVICE_SYNC_TIME,
)
from .migrate_yaml import async_import_yaml


def _coord(hass: HomeAssistant, mac: str):
    coord = hass.data.get(DOMAIN, {}).get(mac)
    if coord is None:
        raise ServiceValidationError(f"Gateway {mac} not found", translation_domain=DOMAIN)
    return coord


async def async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_SYNC_TIME):
        return

    async def _sync_time(call: ServiceCall) -> None:
        coord = _coord(hass, call.data["gateway"])
        await coord.send(OWNGatewayCommand.set_datetime_to_now(str(hass.config.time_zone)))

    async def _send_message(call: ServiceCall) -> None:
        coord = _coord(hass, call.data["gateway"])
        await coord.send_raw(call.data["message"])

    async def _import_yaml(call: ServiceCall) -> None:
        await async_import_yaml(hass, call.data["path"])

    hass.services.async_register(
        DOMAIN, SERVICE_SYNC_TIME, _sync_time, schema=vol.Schema({vol.Required("gateway"): cv.string})
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_MESSAGE,
        _send_message,
        schema=vol.Schema({vol.Required("gateway"): cv.string, vol.Required("message"): cv.string}),
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_IMPORT_YAML,
        _import_yaml,
        schema=vol.Schema({vol.Optional("path", default="/config/myhome.yaml"): cv.string}),
    )
    LOGGER.info("MyHOME services registered")