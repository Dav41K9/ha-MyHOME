"""Power / energy / temperature / illuminance sensors."""
from __future__ import annotations

from OWNd.message import (
    MESSAGE_TYPE_ACTIVE_POWER,
    MESSAGE_TYPE_ENERGY_TOTALIZER,
    MESSAGE_TYPE_ILLUMINANCE,
    MESSAGE_TYPE_MAIN_TEMPERATURE,
    MESSAGE_TYPE_SECONDARY_TEMPERATURE,
    OWNEnergyCommand,
    OWNEnergyEvent,
    OWNHeatingCommand,
    OWNHeatingEvent,
    OWNLightingCommand,
    OWNLightingEvent,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import LIGHT_LUX, UnitOfEnergy, UnitOfPower, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddEntitiesCallback
import voluptuous as vol

from .const import (
    CONF_DEVICE_CLASS,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_NAME,
    CONF_WHERE,
    SERVICE_START_INSTANT_POWER,
    SUBENTRY_SENSOR,
)
from .entity import MyHOMEEntity

_DC = {
    "power": SensorDeviceClass.POWER,
    "energy": SensorDeviceClass.ENERGY,
    "temperature": SensorDeviceClass.TEMPERATURE,
    "illuminance": SensorDeviceClass.ILLUMINANCE,
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = entry.runtime_data
    entities, has_power = [], False
    for sub in entry.subentries.values():
        if sub.subentry_type != SUBENTRY_SENSOR:
            continue
        dc = _DC.get(sub.data.get(CONF_DEVICE_CLASS, "power"), SensorDeviceClass.POWER)
        if dc == SensorDeviceClass.POWER:
            entities.append(MyHOMEPowerSensor(coord, sub.subentry_id, sub.data))
            has_power = True
        elif dc == SensorDeviceClass.ENERGY:
            entities.append(MyHOMEEnergySensor(coord, sub.subentry_id, sub.data))
        elif dc == SensorDeviceClass.TEMPERATURE:
            entities.append(MyHOMETemperatureSensor(coord, sub.subentry_id, sub.data))
        else:
            entities.append(MyHOMEIlluminanceSensor(coord, sub.subentry_id, sub.data))
    async_add_entities(entities)
    if has_power:
        platform = entity_platform.async_get_current_platform()
        platform.async_register_entity_service(
            SERVICE_START_INSTANT_POWER,
            {vol.Optional("duration", default=65): vol.All(int, vol.Range(min=1, max=255))},
            "start_sending_instant_power",
        )


class MyHOMEPowerSensor(MyHOMEEntity, SensorEntity):
    def __init__(self, coordinator, subentry_id, data):
        super().__init__(coordinator, subentry_id, 18, data[CONF_WHERE], data[CONF_NAME],
                         data.get(CONF_MANUFACTURER, ""), data.get(CONF_MODEL, ""))
        self._attr_device_class = SensorDeviceClass.POWER
        self._attr_native_unit_of_measurement = UnitOfPower.WATT
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_value = None

    async def async_request_initial_state(self) -> None:
        # ask the gateway to push instant power for ~1h (renew via service)
        await self._coordinator.send(OWNEnergyCommand.start_sending_instant_power(self._where, 65))

    async def start_sending_instant_power(self, duration: int) -> None:
        await self._coordinator.send(OWNEnergyCommand.start_sending_instant_power(self._where, duration))

    def handle_event(self, message: OWNEnergyEvent) -> None:
        if message.message_type != MESSAGE_TYPE_ACTIVE_POWER:
            return
        self._attr_native_value = message.active_power
        self.async_write_ha_state()


class MyHOMEEnergySensor(MyHOMEEntity, SensorEntity):
    def __init__(self, coordinator, subentry_id, data):
        super().__init__(coordinator, subentry_id, 18, data[CONF_WHERE], data[CONF_NAME],
                         data.get(CONF_MANUFACTURER, ""), data.get(CONF_MODEL, ""))
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_value = None

    async def async_request_initial_state(self) -> None:
        await self._coordinator.send_status_request(OWNEnergyCommand.get_total_consumption(self._where))

    def handle_event(self, message: OWNEnergyEvent) -> None:
        if message.message_type == MESSAGE_TYPE_ENERGY_TOTALIZER:
            self._attr_native_value = message.total_consumption
            self.async_write_ha_state()


class MyHOMETemperatureSensor(MyHOMEEntity, SensorEntity):
    def __init__(self, coordinator, subentry_id, data):
        super().__init__(coordinator, subentry_id, 4, data[CONF_WHERE], data[CONF_NAME],
                         data.get(CONF_MANUFACTURER, ""), data.get(CONF_MODEL, ""))
        self._attr_device_class = SensorDeviceClass.TEMPERATURE
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_value = None

    async def async_request_initial_state(self) -> None:
        await self._coordinator.send_status_request(OWNHeatingCommand.get_temperature(self._where))

    def handle_event(self, message: OWNHeatingEvent) -> None:
        if message.message_type == MESSAGE_TYPE_MAIN_TEMPERATURE:
            self._attr_native_value = message.main_temperature
            self.async_write_ha_state()
        elif message.message_type == MESSAGE_TYPE_SECONDARY_TEMPERATURE:
            self._attr_native_value = message.secondary_temperature
            self.async_write_ha_state()


class MyHOMEIlluminanceSensor(MyHOMEEntity, SensorEntity):
    def __init__(self, coordinator, subentry_id, data):
        super().__init__(coordinator, subentry_id, 1, data[CONF_WHERE], data[CONF_NAME],
                         data.get(CONF_MANUFACTURER, ""), data.get(CONF_MODEL, ""))
        self._attr_device_class = SensorDeviceClass.ILLUMINANCE
        self._attr_native_unit_of_measurement = LIGHT_LUX
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_value = None

    async def async_request_initial_state(self) -> None:
        await self._coordinator.send_status_request(OWNLightingCommand.get_illuminance(self._where))

    def handle_event(self, message: OWNLightingEvent) -> None:
        if message.message_type != MESSAGE_TYPE_ILLUMINANCE:
            return
        self._attr_native_value = message.illuminance
        self.async_write_ha_state()