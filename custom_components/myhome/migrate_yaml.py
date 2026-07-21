"""One-time migration: reads old myhome.yaml and creates subentries.

Usage: call the service myhome.migrate_yaml from Developer Tools > Services,
or run manually via a script.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry

from .const import DOMAIN, OLD_YAML_PATH

_LOGGER = logging.getLogger(__name__)

PLATFORM_MAP = {
    "light": "light",
    "switch": "switch",
    "cover": "cover",
    "climate": "climate",
    "sensor": "sensor",
    "binary_sensor": "binary_sensor",
    "button": "button",
}


async def async_migrate_yaml_to_subentries(hass: HomeAssistant) -> str:
    """Read myhome.yaml and create subentries for all devices."""
    yaml_path = Path(hass.config.path(OLD_YAML_PATH))
    if not yaml_path.exists():
        return "File myhome.yaml non trovato. Niente da migrare."

    with open(yaml_path) as f:
        config = yaml.safe_load(f)

    if not config:
        return "File myhome.yaml vuoto."

    results: list[str] = []

    for gateway_name, gateway_config in config.items():
        if not isinstance(gateway_config, dict):
            continue

        mac = str(gateway_config.get("mac", ""))
        if not mac:
            results.append(f"⚠️ Gateway '{gateway_name}': nessun MAC, saltato.")
            continue

        # Find the config entry for this gateway
        entry: ConfigEntry | None = None
        for e in hass.config_entries.async_entries(DOMAIN):
            if str(e.data.get("mac", "")).lower() == mac.lower():
                entry = e
                break

        if not entry:
            results.append(
                f"⚠️ Gateway '{gateway_name}' (MAC {mac}): "
                f"nessun config entry trovato. Aggiungi prima il gateway via UI."
            )
            continue

        count = 0
        for platform, devices in gateway_config.items():
            if platform == "mac":
                continue
            subentry_type = PLATFORM_MAP.get(platform)
            if not subentry_type or not isinstance(devices, dict):
                continue

            for device_id, device_config in devices.items():
                if not isinstance(device_config, dict):
                    continue

                where = str(
                    device_config.get("where", device_config.get("zone", ""))
                )
                name = str(device_config.get("name", device_id))

                data = {
                    "device_type": subentry_type,
                    "name": name,
                    "where": where,
                    "dimmable": bool(device_config.get("dimmable", False)),
                    "advanced": bool(device_config.get("advanced", False)),
                    "zone": str(device_config.get("zone", "")),
                    "heat": bool(device_config.get("heat", True)),
                    "cool": bool(device_config.get("cool", False)),
                    "standalone": bool(device_config.get("standalone", True)),
                    "sensor_class": str(device_config.get("class", "power")),
                    "device_class": str(device_config.get("class", "outlet")),
                    "manufacturer": str(
                        device_config.get("manufacturer", "BTicino")
                    ),
                    "model": str(device_config.get("model", "")),
                }

                unique_id = f"{subentry_type}-{where}"

                # Check if subentry already exists
                exists = any(
                    s.unique_id == unique_id
                    for s in entry.subentries.values()
                )
                if exists:
                    continue

                try:
                    await hass.config_entries.async_add_subentry(
                        entry,
                        {
                            "title": name,
                            "data": data,
                            "subentry_type": subentry_type,
                            "unique_id": unique_id,
                        },
                    )
                    count += 1
                except Exception:
                    _LOGGER.exception(
                        "Failed to create subentry %s for %s",
                        unique_id, name,
                    )

        results.append(f"✅ Gateway '{gateway_name}': {count} dispositivi migrati.")

    return "\n".join(results)
