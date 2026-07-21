"""Diagnostics support for BTicino MyHOME."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import CONF_PASSWORD, DOMAIN


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    data = dict(entry.data)
    if CONF_PASSWORD in data:
        data[CONF_PASSWORD] = "**REDACTED**"

    subentries = {}
    for sid, sub in entry.subentries.items():
        subentries[sid] = {
            "type": sub.subentry_type,
            "title": sub.title,
            "data": sub.data,
        }

    return {
        "entry": data,
        "subentries": subentries,
        "subentry_count": len(subentries),
    }
