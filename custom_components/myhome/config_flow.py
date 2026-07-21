"""Config flow for BTicino MyHOME integration."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import voluptuous as vol
import yaml

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .const import (
    CONF_ADVANCED,
    CONF_COOL,
    CONF_DEVICE_CLASS,
    CONF_DEVICE_TYPE,
    CONF_DIMMABLE,
    CONF_GATEWAY_NAME,
    CONF_HEAT,
    CONF_HOST,
    CONF_MAC,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_SENSOR_CLASS,
    CONF_STANDALONE,
    CONF_WHERE,
    CONF_ZONE,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DOMAIN,
    OLD_YAML_PATH,
    SUBENTRY_CLIMATE,
    SUBENTRY_COVER,
    SUBENTRY_LIGHT,
    SUBENTRY_SENSOR,
    SUBENTRY_SWITCH,
)

_LOGGER = logging.getLogger(__name__)

GATEWAY_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_GATEWAY_NAME): TextSelector(
            TextSelectorConfig(type="text")
        ),
        vol.Required(CONF_HOST): TextSelector(TextSelectorConfig(type="text")),
        vol.Required(CONF_PORT, default=DEFAULT_PORT): vol.Coerce(int),
        vol.Required(CONF_PASSWORD, default=DEFAULT_PASSWORD): TextSelector(
            TextSelectorConfig(type="password")
        ),
        vol.Required(CONF_MAC): TextSelector(TextSelectorConfig(type="text")),
    }
)

DEVICE_TYPE_SELECTOR = SelectSelector(
    SelectSelectorConfig(
        options=[
            {"value": SUBENTRY_LIGHT, "label": "Luce"},
            {"value": SUBENTRY_SWITCH, "label": "Switch / Presa"},
            {"value": SUBENTRY_COVER, "label": "Tapparella / Tenda"},
            {"value": SUBENTRY_CLIMATE, "label": "Termostato / Zona"},
            {"value": SUBENTRY_SENSOR, "label": "Sensore (potenza)"},
        ],
        mode=SelectSelectorMode.DROPDOWN,
    )
)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DEVICE_TYPE): DEVICE_TYPE_SELECTOR,
        vol.Required(CONF_NAME): TextSelector(TextSelectorConfig(type="text")),
        vol.Required(CONF_WHERE): TextSelector(TextSelectorConfig(type="text")),
        vol.Optional(CONF_DIMMABLE, default=False): BooleanSelector(),
        vol.Optional(CONF_ADVANCED, default=False): BooleanSelector(),
        vol.Optional(CONF_ZONE, default="1"): TextSelector(
            TextSelectorConfig(type="text")
        ),
        vol.Optional(CONF_HEAT, default=True): BooleanSelector(),
        vol.Optional(CONF_COOL, default=False): BooleanSelector(),
        vol.Optional(CONF_STANDALONE, default=True): BooleanSelector(),
        vol.Optional(CONF_SENSOR_CLASS, default="power"): TextSelector(
            TextSelectorConfig(type="text")
        ),
        vol.Optional(CONF_DEVICE_CLASS, default="outlet"): TextSelector(
            TextSelectorConfig(type="text")
        ),
        vol.Optional(CONF_MANUFACTURER, default="BTicino"): TextSelector(
            TextSelectorConfig(type="text")
        ),
        vol.Optional(CONF_MODEL, default=""): TextSelector(
            TextSelectorConfig(type="text")
        ),
    }
)

DEVICE_RECONFIGURE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): TextSelector(TextSelectorConfig(type="text")),
        vol.Required(CONF_WHERE): TextSelector(TextSelectorConfig(type="text")),
        vol.Optional(CONF_DIMMABLE, default=False): BooleanSelector(),
        vol.Optional(CONF_ADVANCED, default=False): BooleanSelector(),
        vol.Optional(CONF_ZONE, default="1"): TextSelector(
            TextSelectorConfig(type="text")
        ),
        vol.Optional(CONF_HEAT, default=True): BooleanSelector(),
        vol.Optional(CONF_COOL, default=False): BooleanSelector(),
        vol.Optional(CONF_STANDALONE, default=True): BooleanSelector(),
        vol.Optional(CONF_SENSOR_CLASS, default="power"): TextSelector(
            TextSelectorConfig(type="text")
        ),
        vol.Optional(CONF_DEVICE_CLASS, default="outlet"): TextSelector(
            TextSelectorConfig(type="text")
        ),
        vol.Optional(CONF_MANUFACTURER, default="BTicino"): TextSelector(
            TextSelectorConfig(type="text")
        ),
        vol.Optional(CONF_MODEL, default=""): TextSelector(
            TextSelectorConfig(type="text")
        ),
    }
)


class MyHOMEConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BTicino MyHOME."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step: gateway connection."""
        errors: dict[str, str] = {}

        if user_input is not None:
            mac = dr.format_mac(str(user_input[CONF_MAC]))
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()

            # Test connection
            try:
                from OWNd import OWNdGateway

                gw = OWNdGateway(
                    address=str(user_input[CONF_HOST]),
                    port=int(user_input[CONF_PORT]),
                    password=str(user_input[CONF_PASSWORD]),
                    mac=mac,
                )
                connected = await asyncio.wait_for(
                    gw.async_connect(), timeout=10
                )
                if connected:
                    await gw.async_disconnect()
                else:
                    errors["base"] = "cannot_connect"
            except asyncio.TimeoutError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during gateway setup")
                errors["base"] = "unknown"

            if not errors:
                user_input[CONF_MAC] = mac
                return self.async_create_entry(
                    title=str(user_input[CONF_GATEWAY_NAME]),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=GATEWAY_SCHEMA,
            errors=errors,
        )

    async def async_step_ssdp(self, discovery_info: dict) -> ConfigFlowResult:
        """Handle SSDP discovery."""
        mac = discovery_info.get("mac", "")
        if mac:
            mac = dr.format_mac(str(mac))
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured()

        self.context["title_placeholders"] = {
            "name": discovery_info.get("name", "MyHOME Gateway")
        }

        return await self.async_step_user()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of gateway."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            mac = dr.format_mac(str(user_input[CONF_MAC]))
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_mismatch()
            user_input[CONF_MAC] = mac
            return self.async_update_reload_and_abort(
                entry, data_updates=user_input
            )

        schema = self.add_suggested_values_to_schema(
            GATEWAY_SCHEMA, entry.data
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentry types supported by this integration."""
        return {
            SUBENTRY_LIGHT: MyHOMEDeviceSubentryFlow,
            SUBENTRY_SWITCH: MyHOMEDeviceSubentryFlow,
            SUBENTRY_COVER: MyHOMEDeviceSubentryFlow,
            SUBENTRY_CLIMATE: MyHOMEDeviceSubentryFlow,
            SUBENTRY_SENSOR: MyHOMEDeviceSubentryFlow,
        }


class MyHOMEDeviceSubentryFlow(ConfigSubentryFlow):
    """Handle subentry flow for adding/modifying a MyHOME device."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """User flow to add a new device."""
        errors: dict[str, str] = {}

        if user_input is not None:
            device_type = str(user_input[CONF_DEVICE_TYPE])
            where = str(user_input[CONF_WHERE])
            name = str(user_input[CONF_NAME])

            unique_id = f"{device_type}-{where}"
            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            # Ensure manufacturer/model are strings (fix for the list bug)
            user_input[CONF_MANUFACTURER] = str(
                user_input.get(CONF_MANUFACTURER, "BTicino")
            )
            user_input[CONF_MODEL] = str(user_input.get(CONF_MODEL, ""))

            return self.async_create_entry(
                title=name,
                data=user_input,
                subentry_type=device_type,
            )

        return self.async_show_form(
            step_id="user",
            data_schema=DEVICE_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Reconfigure an existing device subentry."""
        subentry = self._get_reconfigure_subentry()
        errors: dict[str, str] = {}

        if user_input is not None:
            user_input[CONF_MANUFACTURER] = str(
                user_input.get(CONF_MANUFACTURER, "BTicino")
            )
            user_input[CONF_MODEL] = str(user_input.get(CONF_MODEL, ""))

            return self.async_update_and_abort(
                self._get_entry(),
                subentry,
                data=user_input,
            )

        schema = self.add_suggested_values_to_schema(
            DEVICE_RECONFIGURE_SCHEMA, subentry.data
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )
