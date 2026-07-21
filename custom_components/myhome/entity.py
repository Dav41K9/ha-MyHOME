"""Base entity for BTicino MyHOME integration."""
from __future__ import annotations

from homeassistant.helpers.entity import Entity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import MyHOMEGatewayCoordinator

class MyHOMEEntity(CoordinatorEntity[MyHOMEGatewayCoordinator], Entity):
    """Base entity for BTicino MyHOME integration."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: MyHOMEGatewayCoordinator,
        device_name: str,
        where: str,
        mac: str,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._where = where
        self._attr_name = device_name
        self._attr_unique_id = f"{mac}-{where}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{mac}-{where}")},
            name=device_name,
            manufacturer=MANUFACTURER,
            model=MODEL,
            via_device=(DOMAIN, mac),  # Collegamento al gateway
            configuration_url=f"http://{coordinator.host}:{coordinator.port}",
        )