"""Switch platform for BTicino MyHOME."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_DEVICE_CLASS,
    SUBENTRY_SWITCH,
    WHO_LIGHTING,
)
from .coordinator import MyHOMEGatewayCoordinator
from .entity import MyHOMEEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MyHOME switches from config entry subentries."""
    coordinator: MyHOMEGatewayCoordinator = entry.runtime_data

    entities = []
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == SUBENTRY_SWITCH:
            entities.append(
                MyHOMESwitch(coordinator, entry, subentry_id, subentry.data)
            )

    async_add_entities(entities)


class MyHOMESwitch(MyHOMEEntity, SwitchEntity):
    """Representation of a MyHOME switch."""

    def __init__(self, coordinator, entry, subentry_id, data) -> None:
        super().__init__(coordinator, entry, subentry_id, data)
        self._attr_is_on = False
        dc = str(data.get(CONF_DEVICE_CLASS, "outlet"))
        if dc == "outlet":
            self._attr_device_class = SwitchDeviceClass.OUTLET
        else:
            self._attr_device_class = SwitchDeviceClass.SWITCH

    def _get_who(self) -> int:
        return WHO_LIGHTING

    async def _async_request_initial_state(self) -> None:
        message = await self._coordinator.async_request_state(
            WHO_LIGHTING, self._where
        )
        if message:
            what = str(getattr(message, "what", ""))
            self._attr_is_on = what == "1"

    @callback
    def _handle_event(self, message) -> None:
        what = str(getattr(message, "what", ""))
        self._attr_is_on = what == "1"
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._coordinator.async_send_message(
            f"*1*1*{self._where}##"
        )
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._coordinator.async_send_message(
            f"*1*0*{self._where}##"
        )
        self._attr_is_on = False
        self.async_write_ha_state()
