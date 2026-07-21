"""Binary sensor platform for BTicino MyHOME."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_DEVICE_CLASS,
    CONF_OFF_VALUE,
    CONF_ON_VALUE,
    CONF_WHO,
    SUBENTRY_BINARY_SENSOR,
    WHO_LIGHTING,
)
from .coordinator import MyHOMEGatewayCoordinator
from .entity import MyHOMEEntity

_LOGGER = logging.getLogger(__name__)

VALID_DEVICE_CLASSES = {dc.value for dc in BinarySensorDeviceClass}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MyHOME binary sensors from config entry subentries."""
    coordinator: MyHOMEGatewayCoordinator = entry.runtime_data

    entities = []
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == SUBENTRY_BINARY_SENSOR:
            entities.append(
                MyHOMEBinarySensor(coordinator, entry, subentry_id, subentry.data)
            )

    async_add_entities(entities)


class MyHOMEBinarySensor(MyHOMEEntity, BinarySensorEntity):
    """Representation of a MyHOME binary sensor (motion, door, window, etc.)."""

    def __init__(self, coordinator, entry, subentry_id, data) -> None:
        super().__init__(coordinator, entry, subentry_id, data)
        self._who: int = int(data.get(CONF_WHO, WHO_LIGHTING))
        self._on_value: str = str(data.get(CONF_ON_VALUE, "1"))
        self._off_value: str = str(data.get(CONF_OFF_VALUE, "0"))
        self._attr_is_on = False

        dc = str(data.get(CONF_DEVICE_CLASS, "motion"))
        if dc in VALID_DEVICE_CLASSES:
            self._attr_device_class = BinarySensorDeviceClass(dc)

    def _get_who(self) -> int:
        return self._who

    async def _async_request_initial_state(self) -> None:
        message = await self._coordinator.async_request_state(
            self._who, self._where
        )
        if message:
            self._parse_state(message)

    @callback
    def _handle_event(self, message) -> None:
        self._parse_state(message)
        self.async_write_ha_state()

    @callback
    def _parse_state(self, message) -> None:
        what = str(getattr(message, "what", ""))
        if what == self._on_value:
            self._attr_is_on = True
        elif what == self._off_value:
            self._attr_is_on = False
