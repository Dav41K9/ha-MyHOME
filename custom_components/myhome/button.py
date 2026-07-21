"""Button platform for BTicino MyHOME."""

from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_FRAME,
    SUBENTRY_BUTTON,
)
from .coordinator import MyHOMEGatewayCoordinator
from .entity import MyHOMEEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up MyHOME buttons from config entry subentries."""
    coordinator: MyHOMEGatewayCoordinator = entry.runtime_data

    entities = []
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == SUBENTRY_BUTTON:
            entities.append(
                MyHOMEButton(coordinator, entry, subentry_id, subentry.data)
            )

    async_add_entities(entities)


class MyHOMEButton(MyHOMEEntity, ButtonEntity):
    """Representation of a MyHOME button (sends a custom OWNd frame)."""

    def __init__(self, coordinator, entry, subentry_id, data) -> None:
        super().__init__(coordinator, entry, subentry_id, data)
        self._frame: str = str(data.get(CONF_FRAME, ""))

    async def async_press(self) -> None:
        """Send the configured OWNd frame to the gateway."""
        if self._frame:
            await self._coordinator.async_send_message(self._frame)
            _LOGGER.debug(
                "Button '%s' sent frame `%s` to gateway %s",
                self.name, self._frame, self._coordinator.mac,
            )
