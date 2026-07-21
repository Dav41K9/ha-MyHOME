"""One-time migration: reads old myhome.yaml and creates subentries.

Usage: call the service myhome.migrate_yaml from Developer Tools > Services.
"""

from __future__ import annotations

import inspect
import logging
from pathlib import Path

import yaml

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, OLD_YAML_PATH

_LOGGER = logging.getLogger(__name__)

# ConfigSubentry may live in different places across HA versions
try:
    from homeassistant.config_entries import ConfigSubentry
except ImportError:  # pragma: no cover
    ConfigSubentry = None  # type: ignore[assignment]

PLATFORM_MAP = {
    "light": "light",
    "switch": "switch",
    "cover": "cover",
    "climate": "climate",
    "sensor": "sensor",
    "binary_sensor": "binary_sensor",
    "button": "button",
}


async def _add_one(
    hass: HomeAssistant,
    entry: ConfigEntry,
    data: dict,
    subentry_type: str,
    name: str,
    unique_id: str,
) -> None:
    """Add a single subentry, trying the different API signatures HA may expose."""
    fn = getattr(hass.config_entries, "async_add_subentry", None)
    if fn is None:
        raise RuntimeError(
            "hass.config_entries.async_add_subentry non disponibile in questa versione di HA"
        )

    strategies: list[tuple[str, Any]] = []
    if ConfigSubentry is not None:
        strategies.append(
            (
                "ConfigSubentry(pos)",
                lambda: fn(
                    entry,
                    ConfigSubentry(
                        data=data,
                        subentry_type=subentry_type,
                        title=name,
                        unique_id=unique_id,
                    ),
                ),
            )
        )
    strategies.append(
        (
            "kwargs",
            lambda: fn(
                entry,
                data=data,
                subentry_type=subentry_type,
                title=name,
                unique_id=unique_id,
            ),
        )
    )
    strategies.append(
        (
            "dict(pos)",
            lambda: fn(
                entry,
                {
                    "data": data,
                    "subentry_type": subentry_type,
                    "title": name,
                    "unique_id": unique_id,
                },
            ),
        )
    )

    last_exc: Exception | None = None
    for _label, make in strategies:
        try:
            res = make()
            if inspect.isawaitable(res):
                await res
            return  # success
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            # If despite the exception the subentry appeared, treat as success
            if any(s.unique_id == unique_id for s in entry.subentries.values()):
                return
            continue

    if last_exc is not None:
        raise last_exc


# Type alias used in _add_one signature above
from typing import Any  # noqa: E402  (kept late to avoid clutter at top)


async def async_migrate_yaml_to_subentries(hass: HomeAssistant) -> str:
    """Read myhome.yaml and create subentries for all devices."""

    candidates = [
        Path(hass.config.path(OLD_YAML_PATH)),
        Path(hass.config.config_dir).parent / OLD_YAML_PATH,
    ]

    yaml_path: Path | None = None
    for candidate in candidates:
        if candidate.exists():
            yaml_path = candidate
            break

    if yaml_path is None:
        paths_tried = ", ".join(str(c) for c in candidates)
        return f"File myhome.yaml non trovato. Percorsi provati: {paths_tried}"

    _LOGGER.info("Trovato myhome.yaml in: %s", yaml_path)

    with open(yaml_path) as f:
        config = yaml.safe_load(f)

    if not config:
        return "File myhome.yaml vuoto."

    results: list[str] = []
    errors: list[str] = []

    for gateway_name, gateway_config in config.items():
        if not isinstance(gateway_config, dict):
            continue

        mac = str(gateway_config.get("mac", ""))
        if not mac:
            results.append(f"⚠️ Gateway '{gateway_name}': nessun MAC, saltato.")
            continue

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
        gw_errors = 0
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

                if any(s.unique_id == unique_id for s in entry.subentries.values()):
                    continue  # already migrated

                try:
                    await _add_one(hass, entry, data, subentry_type, name, unique_id)
                    count += 1
                except Exception as exc:  # noqa: BLE001
                    gw_errors += 1
                    msg = f"{unique_id} ({name}): {type(exc).__name__}: {exc}"
                    errors.append(msg)
                    _LOGGER.error(
                        "Failed to create subentry %s: %s",
                        msg,
                        exc_info=exc,
                    )

        if gw_errors:
            results.append(
                f"⚠️ Gateway '{gateway_name}': {count} creati, {gw_errors} falliti."
            )
        else:
            results.append(f"✅ Gateway '{gateway_name}': {count} dispositivi migrati.")

    summary = "\n".join(results)
    if errors:
        summary += "\n\nErrori riscontrati:\n- " + "\n- ".join(errors[:30])
    return summary
