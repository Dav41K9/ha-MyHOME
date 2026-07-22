"""Diagnostics download."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    coord = entry.runtime_data
    redacted_data = {k: ("**REDACTED**" if k == CONF_PASSWORD else v) for k, v in entry.data.items()}
    return {
        "config_entry": {"title": entry.title, "data": redacted_data},
        "subentries": [
            {"id": s.subentry_id, "type": s.subentry_type, "title": s.title, "data": dict(s.data)}
            for s in entry.subentries.values()
        ],
        "gateway": {
            "mac": coord.mac,
            "host": coord.host,
            "port": coord.port,
            "is_connected": coord.is_connected,
            "model": coord.model,
            "firmware": coord.firmware,
        },
    }
