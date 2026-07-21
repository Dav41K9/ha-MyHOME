"""Base entity for BTicino MyHOME devices."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity

from .const import (
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_NAME,
    CONF_WHERE,
    DOMAIN,
    SIGNAL_MYHOME_EVENT,
)
from .coordinator import MyHOMEGatewayCoordinator

_LOGGER = logging.getLogger(__name__)


class MyHOMEEntity(Entity):
    """Base class for all MyHOME entities."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: MyHOMEGatewayCoordinator,
        entry: ConfigEntry,
        subentry_id: str,
        subentry_data: dict,
    ) -> None:
        self._coordinator = coordinator
        self._entry = entry
        self._subentry_id = subentry_id
        self._subentry_data = subentry_data

        self._where: str = str(subentry_data.get(CONF_WHERE, ""))
        self._attr_name: str = str(subentry_data.get(CONF_NAME, "MyHOME Device"))

        mac = coordinator.mac
        self._attr_unique_id = f"{mac}-{subentry_id}"

        # FIX: force manufacturer/model to string (old code passed a list)
        manufacturer = str(subentry_data.get(CONF_MANUFACTURER, "BTicino"))
        model = str(subentry_data.get(CONF_MODEL, ""))

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{mac}-{self._where}")},
            name=self._attr_name,
            manufacturer=manufacturer,
            model=model,
            via_device=(DOMAIN, mac),
        )

    async def async_added_to_hass(self) -> None:
        """Register event listener and request initial state."""
        who = self._get_who()
        signal = SIGNAL_MYHOME_EVENT.format(
            mac=self._coordinator.mac, who=str(who), where=self._where
        )
        self.async_on_remove(
            async_dispatcher_connect(self.hass, signal, self._handle_event)
        )

        # Request initial state (replaces the old broken polling)
        await self._async_request_initial_state()

    async def _async_request_initial_state(self) -> None:
        """Request the initial state from the gateway. Override in subclasses."""

    def _get_who(self) -> int:
        """Return the OWNd WHO for this entity type. Override in subclasses."""
        return 1

    def _handle_event(self, message) -> None:
        """Handle an incoming OWNd message. Override in subclasses."""
        self.async_write_ha_state()
