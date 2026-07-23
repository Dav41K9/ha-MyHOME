"""Base entity."""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN, MANUFACTURER_DEFAULT
from .coordinator import MyHOMEGatewayCoordinator


class MyHOMEEntity(Entity):
    """Base class; binds to the per-subentry device created in __init__."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: MyHOMEGatewayCoordinator,
        subentry_id: str,
        who: int,
        where: str,
        name: str,
        manufacturer: str,
        model: str,
    ) -> None:
        self._coordinator = coordinator
        self._subentry_id = subentry_id
        self._who = who
        self._where = where
        self._device_key = f"{coordinator.mac}-{subentry_id}"
        self._attr_unique_id = self._device_key
        # entity name None -> displayed as the device name (single-entity device)
        self._attr_name = None
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_key)},
            name=name,
            manufacturer=manufacturer or MANUFACTURER_DEFAULT,
            model=model or None,
            via_device=(DOMAIN, coordinator.mac),  # works on 2026.7.2; switch to via_device_id on >=2026.8
        )

    @property
    def entity_key(self) -> str:
        return f"{self._who}-{self._where}"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._coordinator.register(self.entity_key, self)
        await self.async_request_initial_state()

    async def async_will_remove_from_hass(self) -> None:
        self._coordinator.unregister(self.entity_key, self)
        await super().async_will_remove_from_hass()

    async def async_request_initial_state(self) -> None:
        """Override to ask the gateway the current state."""

    def handle_event(self, message) -> None:  # pragma: no cover
        raise NotImplementedError