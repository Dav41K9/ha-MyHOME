"""Config flow (hub) + options flow (manage devices)."""
from __future__ import annotations

import re
from typing import Any
from uuid import uuid4

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import ssdp
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlowResult,
    OptionsFlow,
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
    OPTIONS_DEVICES,
    SUBENTRY_BINARY_SENSOR,
    SUBENTRY_CLIMATE,
    SUBENTRY_COVER,
    SUBENTRY_LIGHT,
    SUBENTRY_SENSOR,
    SUBENTRY_SWITCH,
)

_MAC_RE = re.compile(r"^[0-9a-fA-F]{12}$")

_DEFAULT_MODEL = {
    SUBENTRY_LIGHT: "BMSW1005",
    SUBENTRY_SWITCH: "BMSW1005",
    SUBENTRY_COVER: "F411/4",
    SUBENTRY_CLIMATE: "F430R8",
    SUBENTRY_SENSOR: "F520",
    SUBENTRY_BINARY_SENSOR: "BMSW1005",
}


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


def _schema_for_type(dtype: str, defaults: dict | None = None) -> vol.Schema:
    """Build the device form schema for a given type (add or edit)."""

    def d(key: str, fallback: Any) -> Any:
        return defaults.get(key, fallback) if defaults else fallback

    schema: dict = {
        vol.Required(CONF_NAME, default=d(CONF_NAME, "")): TextSelector(),
        vol.Required(CONF_WHERE, default=d(CONF_WHERE, "")): TextSelector(),
    }

    if dtype == SUBENTRY_LIGHT:
        schema[vol.Optional(CONF_DIMMABLE, default=d(CONF_DIMMABLE, False))] = BooleanSelector()
    elif dtype == SUBENTRY_SWITCH:
        schema[vol.Optional(CONF_DEVICE_CLASS, default=d(CONF_DEVICE_CLASS, "outlet"))] = SelectSelector(
            SelectSelectorConfig(options=["outlet", "switch"], translation_key="switch_class")
        )
    elif dtype == SUBENTRY_COVER:
        schema[vol.Optional(CONF_ADVANCED, default=d(CONF_ADVANCED, True))] = BooleanSelector()
    elif dtype == SUBENTRY_CLIMATE:
        schema[vol.Optional(CONF_HEAT, default=d(CONF_HEAT, True))] = BooleanSelector()
        schema[vol.Optional(CONF_COOL, default=d(CONF_COOL, False))] = BooleanSelector()
        schema[vol.Optional(CONF_STANDALONE, default=d(CONF_STANDALONE, True))] = BooleanSelector()
    elif dtype == SUBENTRY_SENSOR:
        schema[vol.Optional(CONF_DEVICE_CLASS, default=d(CONF_DEVICE_CLASS, "power"))] = SelectSelector(
            SelectSelectorConfig(options=["power", "energy", "temperature", "illuminance"], translation_key="sensor_class")
        )
    elif dtype == SUBENTRY_BINARY_SENSOR:
        schema[vol.Optional(CONF_WHO, default=d(CONF_WHO, 25))] = NumberSelector(
            NumberSelectorConfig(min=1, max=255, mode="box")
        )
        schema[vol.Optional(CONF_DEVICE_CLASS, default=d(CONF_DEVICE_CLASS, "opening"))] = SelectSelector(
            SelectSelectorConfig(
                options=["opening", "door", "window", "motion", "smoke", "gas", "moisture", "problem", "safety"],
                translation_key="binary_class",
            )
        )
        schema[vol.Optional(CONF_INVERTED, default=d(CONF_INVERTED, False))] = BooleanSelector()

    schema[vol.Optional(CONF_MANUFACTURER, default=d(CONF_MANUFACTURER, MANUFACTURER_DEFAULT))] = TextSelector()
    schema[vol.Optional(CONF_MODEL, default=d(CONF_MODEL, _DEFAULT_MODEL.get(dtype, "")))] = TextSelector()

    return vol.Schema(schema)


class MyHOMEConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Hub setup flow."""

    VERSION = 2  # bumped from 1: devices moved from subentries to entry.options

    def __init__(self) -> None:
        self._discovered: dict[str, Any] | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return MyHOMEOptionsFlow()

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


class MyHOMEOptionsFlow(OptionsFlow):
    """Manage devices (add / edit / remove) stored in entry.options."""

    def __init__(self) -> None:
        self._dtype: str | None = None
        self._edit_id: str | None = None

    def _devices(self) -> list[dict]:
        return list(self.config_entry.options.get(OPTIONS_DEVICES, []))

    def _save(self, devices: list[dict]) -> ConfigFlowResult:
        new_options = {**self.config_entry.options, OPTIONS_DEVICES: devices}
        return self.async_create_entry(title="", data=new_options)

    def _device_selector(self) -> vol.Schema:
        options = [
            {"value": dev.get("id", ""), "label": dev.get(CONF_NAME, dev.get("id", ""))}
            for dev in self._devices()
        ]
        return vol.Schema(
            {vol.Required("device"): SelectSelector(SelectSelectorConfig(options=options))}
        )

    async def async_step_init(self, user_input: dict | None = None) -> ConfigFlowResult:
        menu = ["add"]
        if self._devices():
            menu += ["edit", "remove"]
        return self.async_show_menu(step_id="init", menu_options=menu)

    async def async_step_add(self, user_input: dict | None = None) -> ConfigFlowResult:
        if user_input is not None:
            self._dtype = user_input["type"]
            return await self.async_step_add_fields()
        return self.async_show_form(
            step_id="add",
            data_schema=vol.Schema(
                {
                    vol.Required("type"): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SUBENTRY_LIGHT,
                                SUBENTRY_SWITCH,
                                SUBENTRY_COVER,
                                SUBENTRY_CLIMATE,
                                SUBENTRY_SENSOR,
                                SUBENTRY_BINARY_SENSOR,
                            ],
                            translation_key="device_type",
                        )
                    )
                }
            ),
        )

    async def async_step_add_fields(self, user_input: dict | None = None) -> ConfigFlowResult:
        assert self._dtype is not None
        if user_input is not None:
            dev = {"id": uuid4().hex, "type": self._dtype}
            dev.update(user_input)
            devices = self._devices()
            devices.append(dev)
            return self._save(devices)
        return self.async_show_form(
            step_id="add_fields",
            data_schema=_schema_for_type(self._dtype),
        )

    async def async_step_edit(self, user_input: dict | None = None) -> ConfigFlowResult:
        devices = self._devices()
        if not devices:
            return await self.async_step_init()
        if user_input is not None:
            self._edit_id = user_input["device"]
            return await self.async_step_edit_fields()
        return self.async_show_form(step_id="edit", data_schema=self._device_selector())

    async def async_step_edit_fields(self, user_input: dict | None = None) -> ConfigFlowResult:
        devices = self._devices()
        current = next((d for d in devices if d.get("id") == self._edit_id), None)
        if current is None:
            return await self.async_step_init()
        if user_input is not None:
            new_dev = {"id": current["id"], "type": current.get("type")}
            new_dev.update(user_input)
            devices = [new_dev if d.get("id") == self._edit_id else d for d in devices]
            return self._save(devices)
        return self.async_show_form(
            step_id="edit_fields",
            data_schema=_schema_for_type(current.get("type", SUBENTRY_LIGHT), defaults=current),
        )

    async def async_step_remove(self, user_input: dict | None = None) -> ConfigFlowResult:
        devices = self._devices()
        if not devices:
            return await self.async_step_init()
        if user_input is not None:
            rid = user_input["device"]
            devices = [d for d in devices if d.get("id") != rid]
            return self._save(devices)
        return self.async_show_form(step_id="remove", data_schema=self._device_selector())
