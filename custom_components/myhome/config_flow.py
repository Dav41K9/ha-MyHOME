"""Config + subentry flows."""
from __future__ import annotations

import re
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    ConfigSubentryFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
)
from OWNd.connection import OWNGateway, OWNSession

from .const import (
    CONF_ADVANCED,
    CONF_COOL,
    CONF_DEVICE_CLASS,
    CONF_DIMMABLE,
    CONF_HEAT,
    CONF_HOST,
    CONF_INVERTED,
    CONF_MAC,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_STANDALONE,
    CONF_WHERE,
    CONF_WHO,
    DEFAULT_NAME,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    DOMAIN,
    LOGGER,
    MANUFACTURER_DEFAULT,
    SUBENTRY_BINARY_SENSOR,
    SUBENTRY_CLIMATE,
    SUBENTRY_COVER,
    SUBENTRY_LIGHT,
    SUBENTRY_SENSOR,
    SUBENTRY_SWITCH,
)

_MAC_RE = re.compile(r"^[0-9a-fA-F]{12}$")


def _normalize_mac(mac: str) -> str:
    raw = re.sub(r"[^0-9a-fA-F]", "", mac or "")
    if not _MAC_RE.match(raw):
        raise ValueError("invalid mac")
    raw = raw.lower()
    return ":".join(raw[i : i + 2] for i in range(0, 12, 2))


def _build_gateway(host: str, port: int, password: str, mac: str, name: str) -> OWNGateway:
    return OWNGateway(
        {
            "address": host,
            "port": port,
            "password": password,
            "serialNumber": mac,
            "modelName": "MyHOME Server",
            "manufacturer": MANUFACTURER_DEFAULT,
            "friendlyName": name,
        }
    )


class MyHOMEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hub setup flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered: dict[str, Any] | None = None

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        return {
            SUBENTRY_LIGHT: LightSubentryFlow,
            SUBENTRY_SWITCH: SwitchSubentryFlow,
            SUBENTRY_COVER: CoverSubentryFlow,
            SUBENTRY_CLIMATE: ClimateSubentryFlow,
            SUBENTRY_SENSOR: SensorSubentryFlow,
            SUBENTRY_BINARY_SENSOR: BinarySensorSubentryFlow,
        }

    def _hub_schema(self) -> vol.Schema:
        d = self._discovered or {}
        return vol.Schema(
            {
                vol.Required(CONF_NAME, default=d.get(CONF_NAME, DEFAULT_NAME)): TextSelector(),
                vol.Required(CONF_HOST, default=d.get(CONF_HOST, "")): TextSelector(),
                vol.Required(CONF_PORT, default=d.get(CONF_PORT, DEFAULT_PORT)): NumberSelector(
                    NumberSelectorConfig(min=1, max=65535, mode="box")
                ),
                vol.Required(CONF_PASSWORD, default=d.get(CONF_PASSWORD, DEFAULT_PASSWORD)): TextSelector(),
                vol.Required(CONF_MAC, default=d.get(CONF_MAC, "")): TextSelector(),
            }
        )

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                mac = _normalize_mac(user_input[CONF_MAC])
            except ValueError:
                errors[CONF_MAC] = "invalid_mac"
            else:
                gw = _build_gateway(
                    user_input[CONF_HOST],
                    int(user_input[CONF_PORT]),
                    str(user_input[CONF_PASSWORD]),
                    mac,
                    user_input[CONF_NAME],
                )
                res = await OWNSession(gateway=gw, logger=LOGGER).test_connection()
                if not res or not res.get("Success"):
                    msg = (res or {}).get("Message")
                    if msg in ("password_required", "password_error", "password_retry"):
                        errors[CONF_PASSWORD] = "invalid_auth"
                    else:
                        errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data={
                            CONF_HOST: user_input[CONF_HOST],
                            CONF_PORT: int(user_input[CONF_PORT]),
                            CONF_PASSWORD: str(user_input[CONF_PASSWORD]),
                            CONF_MAC: mac,
                            CONF_NAME: user_input[CONF_NAME],
                        },
                    )
        return self.async_show_form(step_id="user", data_schema=self._hub_schema(), errors=errors)

    async def async_step_ssdp(self, discovery_info: ssdp.SsdpServiceInfo) -> ConfigFlowResult:
        upnp = discovery_info.upnp or {}
        host = discovery_info.ssdp_headers.get("_host")
        mac_raw = upnp.get("serialNumber") or ""
        try:
            mac = _normalize_mac(mac_raw) if mac_raw else None
        except ValueError:
            mac = None
        self._discovered = {
            CONF_HOST: host or "",
            CONF_PORT: DEFAULT_PORT,
            CONF_NAME: upnp.get("friendlyName") or upnp.get("modelName") or DEFAULT_NAME,
            CONF_MAC: mac or "",
        }
        if mac:
            await self.async_set_unique_id(mac)
            self._abort_if_unique_id_configured(updates={CONF_HOST: host})
        return await self.async_step_user()


# ---------------------------------------------------------------- subentries
class _BaseSubentryFlow(ConfigSubentryFlow):
    SCHEMA: vol.Schema = vol.Schema({})

    async def async_step_user(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=self.SCHEMA)


def _opt_man_model(default_model: str) -> dict:
    return {
        vol.Optional(CONF_MANUFACTURER, default=MANUFACTURER_DEFAULT): TextSelector(),
        vol.Optional(CONF_MODEL, default=default_model): TextSelector(),
    }


class LightSubentryFlow(_BaseSubentryFlow):
    SCHEMA = vol.Schema(
        {
            vol.Required(CONF_NAME): TextSelector(),
            vol.Required(CONF_WHERE): TextSelector(),
            vol.Optional(CONF_DIMMABLE, default=False): BooleanSelector(),
            **_opt_man_model("BMSW1005"),
        }
    )


class SwitchSubentryFlow(_BaseSubentryFlow):
    SCHEMA = vol.Schema(
        {
            vol.Required(CONF_NAME): TextSelector(),
            vol.Required(CONF_WHERE): TextSelector(),
            vol.Optional(CONF_DEVICE_CLASS, default="outlet"): SelectSelector(
                SelectSelectorConfig(options=["outlet", "switch"])
            ),
            **_opt_man_model("BMSW1005"),
        }
    )


class CoverSubentryFlow(_BaseSubentryFlow):
    SCHEMA = vol.Schema(
        {
            vol.Required(CONF_NAME): TextSelector(),
            vol.Required(CONF_WHERE): TextSelector(),
            vol.Optional(CONF_ADVANCED, default=True): BooleanSelector(),
            **_opt_man_model("F411/4"),
        }
    )


class ClimateSubentryFlow(_BaseSubentryFlow):
    SCHEMA = vol.Schema(
        {
            vol.Required(CONF_NAME): TextSelector(),
            vol.Required(CONF_WHERE): TextSelector(),
            vol.Optional(CONF_HEAT, default=True): BooleanSelector(),
            vol.Optional(CONF_COOL, default=False): BooleanSelector(),
            vol.Optional(CONF_STANDALONE, default=True): BooleanSelector(),
            **_opt_man_model("F430R8"),
        }
    )


class SensorSubentryFlow(_BaseSubentryFlow):
    SCHEMA = vol.Schema(
        {
            vol.Required(CONF_NAME): TextSelector(),
            vol.Required(CONF_WHERE): TextSelector(),
            vol.Optional(CONF_DEVICE_CLASS, default="power"): SelectSelector(
                SelectSelectorConfig(options=["power", "energy", "temperature", "illuminance"])
            ),
            **_opt_man_model("F520"),
        }
    )


class BinarySensorSubentryFlow(_BaseSubentryFlow):
    SCHEMA = vol.Schema(
        {
            vol.Required(CONF_NAME): TextSelector(),
            vol.Required(CONF_WHERE): TextSelector(),
            vol.Optional(CONF_WHO, default=25): NumberSelector(
                NumberSelectorConfig(min=1, max=255, mode="box")
            ),
            vol.Optional(CONF_DEVICE_CLASS, default="opening"): SelectSelector(
                SelectSelectorConfig(
                    options=["opening", "door", "window", "motion", "smoke", "gas", "moisture", "problem", "safety"]
                )
            ),
            vol.Optional(CONF_INVERTED, default=False): BooleanSelector(),
            **_opt_man_model("BMSW1005"),
        }
    )
