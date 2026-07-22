"""Setup/unload for BTicino MyHOME."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

from . import services as myhome_services
from .const import (
    CONF_MAC,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_NAME,
    CONF_PASSWORD,
    DOMAIN,
    LOGGER,
    MANUFACTURER_DEFAULT,
    PLATFORMS,
)
from .coordinator import MyHOMEGatewayCoordinator

MyHOMEConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: MyHOMEConfigEntry) -> bool:
    data = dict(entry.data)
    if CONF_MAC not in data or CONF_PASSWORD not in data:
        LOGGER.error(
            "Entry '%s' missing mac/password (old format). Remove and re-add the integration.",
            entry.title,
        )
        return False

    mac = data[CONF_MAC]
    coordinator = MyHOMEGatewayCoordinator(hass, data)
    entry.runtime_data = coordinator

    res = await coordinator.async_test()
    if not res or not res.get("Success"):
        raise ConfigEntryNotReady(f"Gateway {mac} not reachable")

    # ---- device registry: 1 hub device + 1 device per subentry ----
    dev_reg = dr.async_get(hass)
    hub = dev_reg.async_get_or_create(
        config_entry_id=entry.entry_id,
        connections={(dr.CONNECTION_NETWORK_MAC, mac)},
        identifiers={(DOMAIN, mac)},
        manufacturer=MANUFACTURER_DEFAULT,
        name=entry.title,
        model="MyHOME Server",
    )
    coordinator.hub_device_id = hub.id

    current_sub_ids = set(entry.subentries)
    for sub_id, sub in entry.subentries.items():
        dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            config_subentry_id=sub_id,
            identifiers={(DOMAIN, f"{mac}-{sub_id}")},
            name=sub.data.get(CONF_NAME, sub.title),
            manufacturer=sub.data.get(CONF_MANUFACTURER, MANUFACTURER_DEFAULT),
            model=sub.data.get(CONF_MODEL),
            via_device=(DOMAIN, mac),
        )

    # ---- prune orphan devices by identifiers (robust, no internal attrs) ----
    valid_ids = {(DOMAIN, mac)} | {(DOMAIN, f"{mac}-{sid}") for sid in current_sub_ids}
    for dev in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if not (dev.identifiers & valid_ids):
            dev_reg.async_remove_device(dev.id)

    # ---- start gateway loops + platforms + services ----
    await coordinator.async_start()
    hass.data.setdefault(DOMAIN, {})[mac] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await myhome_services.async_register_services(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MyHOMEConfigEntry) -> bool:
    coordinator: MyHOMEGatewayCoordinator = entry.runtime_data
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    await coordinator.async_close()
    hass.data.get(DOMAIN, {}).pop(coordinator.mac, None)
    return ok


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: MyHOMEConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    # Devices are managed via subentries; remove them from the integration page instead.
    return False
