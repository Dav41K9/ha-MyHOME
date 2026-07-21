"""Config flow for BTicino MyHOME integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.config_entries import ConfigEntry, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.schema_validation import multi_select
from OWNd import OWNError, OWNException
from OWNd.command import OWNCommandSession
from OWNd.gateway import OWNGateway

from .const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PORT,
    CONF_SUBENTRY_TYPE,
    CONF_WHERE,
    DEFAULT_HOST,
    DEFAULT_NAME,
    DEFAULT_PORT,
    DOMAIN,
    SUBENTRY_CLIMATE,
    SUBENTRY_COVER,
    SUBENTRY_LIGHT,
    SUBENTRY_SENSOR,
    SUBENTRY_SWITCH,
    SUBENTRY_BUTTON,
    SUBENTRY_BINARY_SENSOR,
)

_LOGGER = logging.getLogger(__name__)

class MyHOMEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BTicino MyHOME."""

    VERSION = 2

    @staticmethod
    @callback
    def async_get_supported_subentry_flows() -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentry flow handlers."""
        return {
            SUBENTRY_LIGHT: MyHOMEDeviceSubentryFlow,
            SUBENTRY_SWITCH: MyHOMEDeviceSubentryFlow,
            SUBENTRY_COVER: MyHOMEDeviceSubentryFlow,
            SUBENTRY_CLIMATE: MyHOMEDeviceSubentryFlow,
            SUBENTRY_SENSOR: MyHOMEDeviceSubentryFlow,
            SUBENTRY_BINARY_SENSOR: MyHOMEDeviceSubentryFlow,
            SUBENTRY_BUTTON: MyHOMEDeviceSubentryFlow,
        }

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                # Verifica connessione gateway
                gateway = OWNGateway(
                    host=user_input[CONF_HOST],
                    port=user_input[CONF_PORT],
                )
                await gateway.connect()
                await gateway.disconnect()
            except OWNException as exc:
                _LOGGER.error("Cannot connect to gateway: %s", exc)
                errors["base"] = "cannot_connect"
            except Exception as exc:
                _LOGGER.exception("Unexpected error: %s", exc)
                errors["base"] = "unknown"

            if not errors:
                await self.async_set_unique_id(
                    f"{user_input[CONF_HOST]}_{user_input[CONF_PORT]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_PORT: user_input[CONF_PORT],
                        CONF_NAME: user_input[CONF_NAME],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_HOST, default=DEFAULT_HOST): str,
                    vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )

    async def async_step_ssdp(
        self, discovery_info: ssdp.SsdpServiceInfo
    ) -> FlowResult:
        """Handle a discovery."""
        _LOGGER.debug("Discovered SSDP device: %s", discovery_info)

        # Estrai dati dal discovery
        host = discovery_info.ssdp_headers["X-IP"]
        port = int(discovery_info.ssdp_headers["X-PORT"])
        name = discovery_info.upnp.get("friendlyName", "BTicino MyHOME")

        await self.async_set_unique_id(f"{host}_{port}")
        self._abort_if_unique_id_configured()

        return await self.async_step_user(
            {
                CONF_NAME: name,
                CONF_HOST: host,
                CONF_PORT: port,
            }
        )

class MyHOMEDeviceSubentryFlow(config_entries.ConfigSubentryFlow):
    """Handle subentry flow for BTicino devices."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle subentry initialization."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_SUBENTRY_TYPE: self.parent_flow.context[CONF_SUBENTRY_TYPE],
                    CONF_WHERE: user_input[CONF_WHERE],
                    CONF_NAME: user_input[CONF_NAME],
                },
            )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_WHERE): str,
                    vol.Required(CONF_NAME): str,
                }
            ),
        )