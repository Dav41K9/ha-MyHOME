"""One-shot import of myhome.yaml -> config subentries."""
from __future__ import annotations

import os
from typing import Any

from homeassistant.config_entries import SOURCE_USER, SubentryFlowContext
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util.yaml import load_yaml

from .const import (
    CONF_ADVANCED,
    CONF_COOL,
    CONF_DEVICE_CLASS,
    CONF_DIMMABLE,
    CONF_HEAT,
    CONF_MAC,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_NAME,
    CONF_STANDALONE,
    CONF_WHERE,
    DOMAIN,
    LOGGER,
    SUBENTRY_CLIMATE,
    SUBENTRY_COVER,
    SUBENTRY_LIGHT,
    SUBENTRY_SENSOR,
    SUBENTRY_SWITCH,
)

# yaml platform key -> subentry type (strings match config_flow subentry types)
_PLATFORMS = ("light", "switch", "cover", "sensor", "climate")


def _normalize_mac(mac: str) -> str:
    raw = "".join(c for c in (mac or "") if c in "0123456789abcdefABCDEF").lower()
    return ":".join(raw[i : i + 2] for i in range(0, 12, 2)) if len(raw) == 12 else (mac or "")


def _map_device(stype: str, name: str, cfg: dict[str, Any]) -> dict[str, Any]:
    base = {
        CONF_NAME: name,
        CONF_MANUFACTURER: cfg.get("manufacturer", "BTicino S.p.A."),
        CONF_MODEL: cfg.get("model", ""),
    }
    if stype == SUBENTRY_CLIMATE:
        return {
            **base,
            CONF_WHERE: str(cfg.get("zone", cfg.get("where", ""))),
            CONF_HEAT: bool(cfg.get("heat", True)),
            CONF_COOL: bool(cfg.get("cool", False)),
            CONF_STANDALONE: bool(cfg.get("standalone", True)),
        }
    data = {**base, CONF_WHERE: str(cfg.get("where", ""))}
    if stype == SUBENTRY_LIGHT:
        data[CONF_DIMMABLE] = bool(cfg.get("dimmable", False))
    elif stype == SUBENTRY_SWITCH:
        data[CONF_DEVICE_CLASS] = cfg.get("class", "outlet")
    elif stype == SUBENTRY_COVER:
        data[CONF_ADVANCED] = bool(cfg.get("advanced", True))
    elif stype == SUBENTRY_SENSOR:
        data[CONF_DEVICE_CLASS] = cfg.get("class", "power")
    return data


async def async_import_yaml(hass: HomeAssistant, path: str) -> dict[str, int]:
    """Read a myhome.yaml file and create subentries for every configured mac."""
    # Resolve relative paths against the HA config dir; absolute paths pass through.
    full_path = hass.config.path(path)

    if not os.path.isfile(full_path):
        raise ServiceValidationError(
            f"File YAML non trovato: {full_path}. "
            "Crea il file (es. /config/myhome.yaml) con la configurazione dei dispositivi e riprova."
        )

    try:
        raw = await hass.async_add_executor_job(load_yaml, full_path)
    except Exception as err:  # noqa: BLE001
        raise ServiceValidationError(f"Errore di lettura YAML in {full_path}: {err}") from err

    if not isinstance(raw, dict):
        raise ServiceValidationError(f"Contenuto YAML non valido in {full_path} (atteso un mapping).")

    # index configured entries by normalized mac
    by_mac = {}
    for entry in hass.config_entries.async_entries(DOMAIN):
        by_mac[_normalize_mac(entry.data.get(CONF_MAC, ""))] = entry

    if not by_mac:
        raise ServiceValidationError("Nessun gateway MyHOME configurato: aggiungi prima gli hub.")

    created: dict[str, int] = {}
    for hub_key, hub_cfg in raw.items():
        if not isinstance(hub_cfg, dict) or "mac" not in hub_cfg:
            continue
        mac = _normalize_mac(hub_cfg["mac"])
        entry = by_mac.get(mac)
        if entry is None:
            LOGGER.warning("import_yaml: no configured entry for mac %s (hub '%s')", mac, hub_key)
            continue

        # avoid duplicates: (subentry_type, where)
        existing = {
            (sub.subentry_type, str(sub.data.get(CONF_WHERE, "")))
            for sub in entry.subentries.values()
        }
        count = 0
        for platform in _PLATFORMS:
            stype = platform
            devices = hub_cfg.get(platform) or {}
            if not isinstance(devices, dict):
                continue
            for _dev_id, dev_cfg in devices.items():
                if not isinstance(dev_cfg, dict):
                    continue
                payload = _map_device(stype, dev_cfg.get("name", _dev_id), dev_cfg)
                key = (stype, payload[CONF_WHERE])
                if key in existing:
                    continue
                await hass.config_entries.subentries.async_init(
                    (entry.entry_id, stype),
                    context=SubentryFlowContext(source=SOURCE_USER),
                    data=payload,
                )
                existing.add(key)
                count += 1
        created[mac] = count
        LOGGER.info("import_yaml: created %d subentries for %s", count, mac)

    if not created:
        raise ServiceValidationError(
            "Nessuna subentry creata: verifica che i MAC nello YAML corrispondano agli hub configurati."
        )
    return created