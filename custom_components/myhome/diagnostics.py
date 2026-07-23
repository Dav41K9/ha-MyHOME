"""Diagnostics download."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_HOST, CONF_MAC, CONF_PASSWORD, OPTIONS_DEVICES

_REDACTED = "**REDACTED**"
_REDACT_DATA = {CONF_PASSWORD, CONF_HOST, CONF_MAC}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    coord = entry.runtime_data
    redacted_data = {k: (_REDACTED if k in _REDACT_DATA else v) for k, v in entry.data.items()}
    return {
        "config_entry": {"title": entry.title, "data": redacted_data},
        "devices": entry.options.get(OPTIONS_DEVICES, []),
        "gateway": {
            "mac": _REDACTED,
            "host": _REDACTED,
            "port": coord.port,
            "is_connected": coord.is_connected,
            "model": coord.model,
            "firmware": coord.firmware,
        },
    }
