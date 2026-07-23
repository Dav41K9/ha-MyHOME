"""Dry contacts (WHO 25), motion (WHO 1), aux (WHO 9)."""
from __future__ import annotations

from OWNd.message import (
    MESSAGE_TYPE_MOTION,
    MESSAGE_TYPE_MOTION_TIMEOUT,
    MESSAGE_TYPE_PIR_SENSITIVITY,
    OWNDryContactCommand,
    OWNDryContactEvent,
    OWNLightingCommand,
    OWNLightingEvent,
)
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DEVICE_CLASS,
    CONF_INVERTED,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_NAME,
    CONF_WHERE,
    CONF_WHO,
    SUBENTRY_BINARY_SENSOR,
)
from .entity import MyHOMEEntity


def _dc(value: str) -> BinarySensorDeviceClass | None:
    return getattr(BinarySensorDeviceClass, value.upper(), None) if value else None


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = entry.runtime_data
    out = []
    for sub in entry.subentries.values():
        if sub.subentry_type != SUBENTRY_BINARY_SENSOR:
            continue
        who = int(sub.data.get(CONF_WHO, 25))
        if who == 1:
            out.append(MyHOMEMotion(coord, sub.subentry_id, sub.data))
        elif who == 9:
            out.append(MyHOMEAux(coord, sub.subentry_id, sub.data))
        else:
            out.append(MyHOMEDryContact(coord, sub.subentry_id, sub.data))
    async_add_entities(out)


class _BaseBinary(MyHOMEEntity, BinarySensorEntity):
    def __init__(self, coordinator, subentry_id, data, who):
        super().__init__(coordinator, subentry_id, who, data[CONF_WHERE], data[CONF_NAME],
                         data.get(CONF_MANUFACTURER, ""), data.get(CONF_MODEL, ""))
        self._inverted = bool(data.get(CONF_INVERTED, False))
        self._attr_device_class = _dc(data.get(CONF_DEVICE_CLASS, ""))
        self._attr_is_on = False


class MyHOMEDryContact(_BaseBinary):
    def __init__(self, c, s, d):
        super().__init__(c, s, d, 25)

    async def async_request_initial_state(self) -> None:
        await self._coordinator.send_status_request(OWNDryContactCommand.status(self._where))

    def handle_event(self, message: OWNDryContactEvent) -> None:
        self._attr_is_on = message.is_on != self._inverted
        self.async_write_ha_state()


class MyHOMEAux(_BaseBinary):
    def __init__(self, c, s, d):
        super().__init__(c, s, d, 9)

    def handle_event(self, message: OWNDryContactEvent) -> None:
        self._attr_is_on = message.is_on != self._inverted
        self.async_write_ha_state()


class MyHOMEMotion(_BaseBinary):
    def __init__(self, c, s, d):
        super().__init__(c, s, d, 1)
        self._attr_device_class = BinarySensorDeviceClass.MOTION

    async def async_request_initial_state(self) -> None:
        await self._coordinator.send_status_request(OWNLightingCommand.get_pir_sensitivity(self._where))

    def handle_event(self, message: OWNLightingEvent) -> None:
        if message.message_type == MESSAGE_TYPE_MOTION:
            self._attr_is_on = bool(message.motion) != self._inverted
            self.async_write_ha_state()
        elif message.message_type in (MESSAGE_TYPE_MOTION_TIMEOUT, MESSAGE_TYPE_PIR_SENSITIVITY):
            self.async_write_ha_state()