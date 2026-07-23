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
    OPTIONS_DEVICES,
    PLATFORMS,
)
from .coordinator import MyHOMEGatewayCoordinator

MyHOMEConfigEntry = ConfigEntry


async def _async_options_updated(hass: HomeAssistant, entry: MyHOMEConfigEntry) -> None:
    """Reload the entry when options (devices) change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: MyHOMEConfigEntry) -> bool:
    """Migrate v1 (subentries) -> v2 (options['devices'])."""
    if entry.version < 2:
        devices: list[dict] = []
        for sub_id, sub in list(entry.subentries.items()):
            dev = {"id": sub_id, "type": sub.subentry_type}
            dev.update(dict(sub.data))
            devices.append(dev)
        new_options = {**entry.options, OPTIONS_DEVICES: devices}
        hass.config_entries.async_update_entry(entry, options=new_options, version=2)
        LOGGER.info("MyHOME: migrated %d devices to options for %s", len(devices), entry.title)
    return True


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

    # ---- device registry: 1 hub device + 1 device per configured device ----
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

    devices = entry.options.get(OPTIONS_DEVICES, [])
    for dev in devices:
        dev_id = dev.get("id")
        if not dev_id:
            continue
        dev_reg.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={(DOMAIN, f"{mac}-{dev_id}")},
            name=dev.get(CONF_NAME, dev_id),
            manufacturer=dev.get(CONF_MANUFACTURER, MANUFACTURER_DEFAULT),
            model=dev.get(CONF_MODEL),
            via_device=(DOMAIN, mac),
        )

    # ---- prune orphan devices by identifiers (robust, no internal attrs) ----
    valid_ids = {(DOMAIN, mac)} | {(DOMAIN, f"{mac}-{d['id']}") for d in devices if d.get("id")}
    for dev in dr.async_entries_for_config_entry(dev_reg, entry.entry_id):
        if not (dev.identifiers & valid_ids):
            dev_reg.async_remove_device(dev.id)

    # ---- drop legacy subentries (data already migrated into options) ----
    for sub_id in list(entry.subentries):
        try:
            await hass.config_entries.async_remove_subentry(entry, sub_id)
        except Exception:  # noqa: BLE001
            LOGGER.debug("Could not remove legacy subentry %s (safe to ignore)", sub_id)

    # ---- start gateway loops + platforms + services ----
    await coordinator.async_start()
    hass.data.setdefault(DOMAIN, {})[mac] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await myhome_services.async_register_services(hass)

    # register reload-on-options AFTER internal updates above (avoid reload during setup)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
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
    """Allow removing a device from the UI by dropping it from options."""
    mac = entry.data[CONF_MAC]
    dev_id: str | None = None
    prefix = f"{mac}-"
    for domain_tag, ident in device_entry.identifiers:
        if domain_tag == DOMAIN and ident.startswith(prefix):
            dev_id = ident[len(prefix):]
            break
    if dev_id is None:
        return False  # hub device: not removable here
    devices = entry.options.get(OPTIONS_DEVICES, [])
    new_devices = [d for d in devices if d.get("id") != dev_id]
    if len(new_devices) == len(devices):
        return False
    new_options = {**entry.options, OPTIONS_DEVICES: new_devices}
    hass.config_entries.async_update_entry(entry, options=new_options)
    return True
