"""Climate platform for BTicino MyHOME."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_COOL,
    CONF_HEAT,
    CONF_ZONE,
    SUBENTRY_CLIMATE,
    WHO_THERMOREGULATION,
)
from .coordinator import MyHOMEGatewayCoordinator
from .entity import MyHOMEEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MyHOME climate from config entry subentries."""
    coordinator: MyHOMEGatewayCoordinator = entry.runtime_data

    entities = []
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == SUBENTRY_CLIMATE:
            entities.append(
                MyHOMEClimate(coordinator, entry, subentry_id, subentry.data)
            )

    async_add_entities(entities)


class MyHOMEClimate(MyHOMEEntity, ClimateEntity):
    """Representation of a MyHOME thermostat zone."""

    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_target_temperature_step = 0.5

    def __init__(self, coordinator, entry, subentry_id, data) -> None:
        super().__init__(coordinator, entry, subentry_id, data)
        self._zone = str(data.get(CONF_ZONE, "1"))
        self._heat = bool(data.get(CONF_HEAT, True))
        self._cool = bool(data.get(CONF_COOL, False))

        self._attr_current_temperature = None
        self._attr_target_temperature = None
        self._attr_hvac_mode = HVACMode.OFF

        modes = [HVACMode.OFF]
        if self._heat:
            modes.append(HVACMode.HEAT)
        if self._cool:
            modes.append(HVACMode.COOL)
        self._attr_hvac_modes = modes

        self._attr_supported_features = ClimateEntityFeature.TARGET_TEMPERATURE

    def _get_who(self) -> int:
        return WHO_THERMOREGULATION

    async def _async_request_initial_state(self) -> None:
        """Request initial temperature from the gateway."""
        message = await self._coordinator.async_request_state(
            WHO_THERMOREGULATION, self._zone
        )
        if message:
            self._parse_state(message)

    @callback
    def _handle_event(self, message) -> None:
        self._parse_state(message)
        self.async_write_ha_state()

    @callback
    def _parse_state(self, message) -> None:
        """Parse thermoregulation messages."""
        try:
            if hasattr(message, "temperature"):
                self._attr_current_temperature = message.temperature
            if hasattr(message, "set_temperature"):
                self._attr_target_temperature = message.set_temperature
        except Exception:
            _LOGGER.debug(
                "Error parsing climate event for zone %s",
                self._zone,
                exc_info=True,
            )

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.HEAT:
            await self._coordinator.async_send_message(
                f"*#4*{self._zone}*11##"
            )
        elif hvac_mode == HVACMode.COOL:
            await self._coordinator.async_send_message(
                f"*#4*{self._zone}*12##"
            )
        elif hvac_mode == HVACMode.OFF:
            await self._coordinator.async_send_message(
                f"*#4*{self._zone}*0##"
            )
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set target temperature."""
        if ATTR_TEMPERATURE in kwargs:
            temp = kwargs[ATTR_TEMPERATURE]
            # OpenWebNet format: temperature * 10, 4 digits
            temp_ownd = int(temp * 10)
            await self._coordinator.async_send_message(
                f"*#4*{self._zone}*{temp_ownd}##"
            )
            self._attr_target_temperature = temp
            self.async_write_ha_state()
