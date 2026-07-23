"""Covers / shutters (WHO 2)."""
from __future__ import annotations

from OWNd.message import OWNAutomationCommand, OWNAutomationEvent
from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_ADVANCED, CONF_MANUFACTURER, CONF_MODEL, CONF_NAME, CONF_WHERE, SUBENTRY_COVER
from .entity import MyHOMEEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = entry.runtime_data
    async_add_entities(
        MyHOMECover(coord, sub.subentry_id, sub.data)
        for sub in entry.subentries.values()
        if sub.subentry_type == SUBENTRY_COVER
    )


class MyHOMECover(MyHOMEEntity, CoverEntity):
    def __init__(self, coordinator, subentry_id: str, data: dict) -> None:
        super().__init__(
            coordinator,
            subentry_id,
            who=2,
            where=data[CONF_WHERE],
            name=data[CONF_NAME],
            manufacturer=data.get(CONF_MANUFACTURER, ""),
            model=data.get(CONF_MODEL, ""),
        )
        self._advanced = bool(data.get(CONF_ADVANCED, True))
        feat = CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        if self._advanced:
            feat |= CoverEntityFeature.SET_POSITION
        self._attr_supported_features = feat
        self._attr_device_class = CoverDeviceClass.SHUTTER
        self._attr_is_closed = None
        self._attr_current_cover_position = None

    async def async_request_initial_state(self) -> None:
        await self._coordinator.send_status_request(OWNAutomationCommand.status(self._where))

    async def async_open_cover(self, **_) -> None:
        await self._coordinator.send(OWNAutomationCommand.raise_shutter(self._where))

    async def async_close_cover(self, **_) -> None:
        await self._coordinator.send(OWNAutomationCommand.lower_shutter(self._where))

    async def async_stop_cover(self, **_) -> None:
        await self._coordinator.send(OWNAutomationCommand.stop_shutter(self._where))

    async def async_set_cover_position(self, **kwargs) -> None:
        if ATTR_POSITION in kwargs:
            await self._coordinator.send(
                OWNAutomationCommand.set_shutter_level(self._where, kwargs[ATTR_POSITION])
            )

    def handle_event(self, message: OWNAutomationEvent) -> None:
        self._attr_is_opening = message.is_opening
        self._attr_is_closing = message.is_closing
        if message.is_closed is not None:
            self._attr_is_closed = message.is_closed
        if message.current_position is not None:
            self._attr_current_cover_position = message.current_position
        self.async_write_ha_state()