"""Cover platform for BTicino MyHOME."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_ADVANCED,
    SUBENTRY_COVER,
    WHO_AUTOMATION,
)
from .coordinator import MyHOMEGatewayCoordinator
from .entity import MyHOMEEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MyHOME covers from config entry subentries."""
    coordinator: MyHOMEGatewayCoordinator = entry.runtime_data

    entities = []
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == SUBENTRY_COVER:
            entities.append(
                MyHOMECover(coordinator, entry, subentry_id, subentry.data)
            )

    async_add_entities(entities)


class MyHOMECover(MyHOMEEntity, CoverEntity):
    """Representation of a MyHOME cover (tapparella/tenda)."""

    _attr_device_class = CoverDeviceClass.SHUTTER

    def __init__(self, coordinator, entry, subentry_id, data) -> None:
        super().__init__(coordinator, entry, subentry_id, data)
        self._advanced = bool(data.get(CONF_ADVANCED, False))
        self._attr_current_cover_position = None
        self._attr_is_closed = None

        if self._advanced:
            self._attr_supported_features = (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
                | CoverEntityFeature.SET_POSITION
            )
        else:
            self._attr_supported_features = (
                CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
                | CoverEntityFeature.STOP
            )

    def _get_who(self) -> int:
        return WHO_AUTOMATION

    async def _async_request_initial_state(self) -> None:
        message = await self._coordinator.async_request_state(
            WHO_AUTOMATION, self._where
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
        # *2*WHERE*0## = stopped, *2*WHERE*1## = opening, *2*WHERE*2## = closing
        if what == "0":
            pass  # stopped, position unknown
        elif what == "1":
            self._attr_is_closed = False
        elif what == "2":
            self._attr_is_closed = True

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._coordinator.async_send_message(
            f"*2*1*{self._where}##"
        )
        self._attr_is_closed = False
        self.async_write_ha_state()

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._coordinator.async_send_message(
            f"*2*2*{self._where}##"
        )
        self._attr_is_closed = True
        self.async_write_ha_state()

    async def async_stop_cover(self, **kwargs: Any) -> None:
        await self._coordinator.async_send_message(
            f"*2*0*{self._where}##"
        )
        self.async_write_ha_state()

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        if ATTR_POSITION in kwargs and self._advanced:
            position = kwargs[ATTR_POSITION]
            await self._coordinator.async_send_message(
                f"*2*11*{self._where}*{position}##"
            )
            self._attr_current_cover_position = position
            self.async_write_ha_state()
