"""Sensor platform for BTicino MyHOME (power monitoring)."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    SUBENTRY_SENSOR,
    WHO_ENERGY,
)
from .coordinator import MyHOMEGatewayCoordinator
from .entity import MyHOMEEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MyHOME sensors from config entry subentries."""
    coordinator: MyHOMEGatewayCoordinator = entry.runtime_data

    entities = []
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == SUBENTRY_SENSOR:
            entities.append(
                MyHOMEPowerSensor(coordinator, entry, subentry_id, subentry.data)
            )

    async_add_entities(entities)


class MyHOMEPowerSensor(MyHOMEEntity, SensorEntity):
    """Representation of a MyHOME power sensor (F520)."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT

    def __init__(self, coordinator, entry, subentry_id, data) -> None:
        super().__init__(coordinator, entry, subentry_id, data)
        self._attr_native_value = None

    def _get_who(self) -> int:
        return WHO_ENERGY

    async def _async_request_initial_state(self) -> None:
        message = await self._coordinator.async_request_state(
            WHO_ENERGY, self._where
        )
        if message:
            self._parse_state(message)

    @callback
    def _handle_event(self, message) -> None:
        self._parse_state(message)
        self.async_write_ha_state()

    @callback
    def _parse_state(self, message) -> None:
        try:
            if hasattr(message, "power"):
                self._attr_native_value = message.power
        except Exception:
            _LOGGER.debug(
                "Error parsing power event for %s",
                self._where,
                exc_info=True,
            )
