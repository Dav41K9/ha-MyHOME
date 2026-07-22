"""Switches / plugs (WHO 1)."""
from __future__ import annotations

from OWNd.message import OWNLightingCommand, OWNLightingEvent
from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE_CLASS, CONF_MANUFACTURER, CONF_MODEL, CONF_NAME, CONF_WHERE, SUBENTRY_SWITCH
from .entity import MyHOMEEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = entry.runtime_data
    async_add_entities(
        MyHOMESwitch(coord, sub.subentry_id, sub.data)
        for sub in entry.subentries.values()
        if sub.subentry_type == SUBENTRY_SWITCH
    )


class MyHOMESwitch(MyHOMEEntity, SwitchEntity):
    def __init__(self, coordinator, subentry_id: str, data: dict) -> None:
        super().__init__(
            coordinator,
            subentry_id,
            who=1,
            where=data[CONF_WHERE],
            name=data[CONF_NAME],
            manufacturer=data.get(CONF_MANUFACTURER, ""),
            model=data.get(CONF_MODEL, ""),
        )
        dc = data.get(CONF_DEVICE_CLASS, "outlet")
        self._attr_device_class = SwitchDeviceClass.OUTLET if dc == "outlet" else SwitchDeviceClass.SWITCH
        self._attr_is_on = None

    async def async_request_initial_state(self) -> None:
        await self._coordinator.send_status_request(OWNLightingCommand.status(self._where))

    async def async_turn_on(self, **_) -> None:
        await self._coordinator.send(OWNLightingCommand.switch_on(self._where))

    async def async_turn_off(self, **_) -> None:
        await self._coordinator.send(OWNLightingCommand.switch_off(self._where))

    def handle_event(self, message: OWNLightingEvent) -> None:
        self._attr_is_on = message.is_on
        self.async_write_ha_state()
