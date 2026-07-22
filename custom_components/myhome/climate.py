"""Heating zones (WHO 4)."""
from __future__ import annotations

from OWNd.message import (
    CLIMATE_MODE_AUTO,
    CLIMATE_MODE_COOL,
    CLIMATE_MODE_HEAT,
    CLIMATE_MODE_OFF,
    MESSAGE_TYPE_ACTION,
    MESSAGE_TYPE_LOCAL_OFFSET,
    MESSAGE_TYPE_LOCAL_TARGET_TEMPERATURE,
    MESSAGE_TYPE_MAIN_HUMIDITY,
    MESSAGE_TYPE_MAIN_TEMPERATURE,
    MESSAGE_TYPE_MODE,
    MESSAGE_TYPE_MODE_TARGET,
    MESSAGE_TYPE_TARGET_TEMPERATURE,
    OWNHeatingCommand,
    OWNHeatingEvent,
)
from homeassistant.components.climate import ClimateEntity, HVACAction, HVACMode
from homeassistant.components.climate.const import ClimateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_COOL,
    CONF_HEAT,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_NAME,
    CONF_STANDALONE,
    CONF_WHERE,
    SUBENTRY_CLIMATE,
)
from .entity import MyHOMEEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = entry.runtime_data
    async_add_entities(
        MyHOMEClimate(coord, sub.subentry_id, sub.data)
        for sub in entry.subentries.values()
        if sub.subentry_type == SUBENTRY_CLIMATE
    )


class MyHOMEClimate(MyHOMEEntity, ClimateEntity):
    def __init__(self, coordinator, subentry_id: str, data: dict) -> None:
        super().__init__(
            coordinator,
            subentry_id,
            who=4,
            where=data[CONF_WHERE],  # zona
            name=data[CONF_NAME],
            manufacturer=data.get(CONF_MANUFACTURER, ""),
            model=data.get(CONF_MODEL, ""),
        )
        self._standalone = bool(data.get(CONF_STANDALONE, True))
        self._heating = bool(data.get(CONF_HEAT, True))
        self._cooling = bool(data.get(CONF_COOL, False))

        self._attr_temperature_unit = UnitOfTemperature.CELSIUS
        self._attr_precision = 0.1
        self._attr_target_temperature_step = 0.5
        self._attr_min_temp = 5
        self._attr_max_temp = 40
        self._attr_supported_features = 0
        self._attr_hvac_modes = [HVACMode.OFF]
        if self._heating or self._cooling:
            self._attr_supported_features |= ClimateEntityFeature.TARGET_TEMPERATURE
            self._attr_hvac_modes.append(HVACMode.AUTO)
        if self._heating:
            self._attr_hvac_modes.append(HVACMode.HEAT)
        if self._cooling:
            self._attr_hvac_modes.append(HVACMode.COOL)

        self._target_temperature = None
        self._local_offset = 0
        self._local_target_temperature = None
        self._attr_current_temperature = None
        self._attr_current_humidity = None
        self._attr_hvac_mode = None
        self._attr_hvac_action = None

    @property
    def target_temperature(self) -> float | None:
        return self._local_target_temperature if self._local_target_temperature is not None else self._target_temperature

    async def async_request_initial_state(self) -> None:
        await self._coordinator.send_status_request(OWNHeatingCommand.status(self._where))

    async def async_set_hvac_mode(self, hvac_mode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._coordinator.send(OWNHeatingCommand.set_mode(self._where, CLIMATE_MODE_OFF, self._standalone))
        elif hvac_mode == HVACMode.AUTO:
            await self._coordinator.send(OWNHeatingCommand.set_mode(self._where, CLIMATE_MODE_AUTO, self._standalone))
        elif hvac_mode == HVACMode.HEAT and self._target_temperature is not None:
            await self._coordinator.send(
                OWNHeatingCommand.set_temperature(self._where, self._target_temperature, CLIMATE_MODE_HEAT, self._standalone)
            )
        elif hvac_mode == HVACMode.COOL and self._target_temperature is not None:
            await self._coordinator.send(
                OWNHeatingCommand.set_temperature(self._where, self._target_temperature, CLIMATE_MODE_COOL, self._standalone)
            )

    async def async_set_temperature(self, **kwargs) -> None:
        target = (kwargs.get("temperature", self._local_target_temperature) or 0) - self._local_offset
        if self._attr_hvac_mode == HVACMode.HEAT:
            mode = CLIMATE_MODE_HEAT
        elif self._attr_hvac_mode == HVACMode.COOL:
            mode = CLIMATE_MODE_COOL
        else:
            mode = CLIMATE_MODE_AUTO
        await self._coordinator.send(OWNHeatingCommand.set_temperature(self._where, target, mode, self._standalone))

    def handle_event(self, message: OWNHeatingEvent) -> None:
        mt = message.message_type
        if mt == MESSAGE_TYPE_MAIN_TEMPERATURE:
            self._attr_current_temperature = message.main_temperature
        elif mt == MESSAGE_TYPE_MAIN_HUMIDITY:
            self._attr_current_humidity = message.main_humidity
        elif mt == MESSAGE_TYPE_TARGET_TEMPERATURE:
            self._target_temperature = message.set_temperature
            self._local_target_temperature = self._target_temperature + self._local_offset
        elif mt == MESSAGE_TYPE_LOCAL_OFFSET:
            self._local_offset = message.local_offset
            if self._target_temperature is not None:
                self._local_target_temperature = self._target_temperature + self._local_offset
        elif mt == MESSAGE_TYPE_LOCAL_TARGET_TEMPERATURE:
            self._local_target_temperature = message.local_set_temperature
            self._target_temperature = self._local_target_temperature - self._local_offset
        elif mt in (MESSAGE_TYPE_MODE, MESSAGE_TYPE_MODE_TARGET):
            m = message.mode
            if m == CLIMATE_MODE_AUTO and HVACMode.AUTO in self._attr_hvac_modes:
                self._attr_hvac_mode = HVACMode.AUTO
                if self._attr_hvac_action == HVACAction.OFF:
                    self._attr_hvac_action = HVACAction.IDLE
            elif m == CLIMATE_MODE_COOL and HVACMode.COOL in self._attr_hvac_modes:
                self._attr_hvac_mode = HVACMode.COOL
                if self._attr_hvac_action == HVACAction.OFF:
                    self._attr_hvac_action = HVACAction.IDLE
            elif m == CLIMATE_MODE_HEAT and HVACMode.HEAT in self._attr_hvac_modes:
                self._attr_hvac_mode = HVACMode.HEAT
                if self._attr_hvac_action == HVACAction.OFF:
                    self._attr_hvac_action = HVACAction.IDLE
            elif m == CLIMATE_MODE_OFF:
                self._attr_hvac_mode = HVACMode.OFF
                self._attr_hvac_action = HVACAction.OFF
            if mt == MESSAGE_TYPE_MODE_TARGET:
                self._target_temperature = message.set_temperature
                self._local_target_temperature = self._target_temperature + self._local_offset
        elif mt == MESSAGE_TYPE_ACTION:
            if message.is_active():
                if self._heating and self._cooling:
                    self._attr_hvac_action = HVACAction.HEATING if message.is_heating() else HVACAction.COOLING
                elif self._heating:
                    self._attr_hvac_action = HVACAction.HEATING
                elif self._cooling:
                    self._attr_hvac_action = HVACAction.COOLING
            elif self._attr_hvac_mode == HVACMode.OFF:
                self._attr_hvac_action = HVACAction.OFF
            else:
                self._attr_hvac_action = HVACAction.IDLE
        self.async_write_ha_state()
