"""Light platform for BTicino MyHOME integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DONT_DIMMABLE,
    CONF_WHERE,
    DOMAIN,
    SUBENTRY_LIGHT,
)
from .entity import MyHOMEEntity
from .coordinator import MyHOMEGatewayCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: dict[str, Any],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up light platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id]
    subentries = entry.subentries

    lights = []
    for subentry_id, subentry in subentries.items():
        if subentry.subentry_type == SUBENTRY_LIGHT:
            lights.append(
                MyHOMELight(
                    coordinator,
                    subentry.data[CONF_WHERE],
                    subentry.data.get(CONF_DONT_DIMMABLE, False),
                    subentry.data[CONF_NAME],
                    coordinator.mac,
                )
            )

    async_add_entities(lights)


class MyHOMELight(MyHOMEEntity, LightEntity):
    """Representation of a BTicino MyHOME light."""

    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature(0)

    def __init__(
        self,
        coordinator: MyHOMEGatewayCoordinator,
        where: str,
        dimmable: bool,
        name: str,
        mac: str,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator, name, where, mac)
        self._dimmable = not dimmable
        self._attr_is_on = False
        self._brightness = 255

    @property
    def is_on(self) -> bool:
        """Return if the light is on."""
        return self._attr_is_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light."""
        return self._brightness

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        _LOGGER.debug("Turning on light %s (where=%s)", self.name, self._where)
        
        if ATTR_BRIGHTNESS in kwargs and self._dimmable:
            brightness = kwargs[ATTR_BRIGHTNESS]
            level = max(1, min(100, int(brightness * 100 / 255)))
            frame = f"*1*1*{self._where}*{level}##"
        else:
            frame = f"*1*1*{self._where}##"
        
        _LOGGER.debug("Sending frame: %s", frame)
        
        try:
            await self.coordinator.async_send_message(frame)
            self._attr_is_on = True
            if ATTR_BRIGHTNESS in kwargs:
                self._brightness = kwargs[ATTR_BRIGHTNESS]
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to turn on light %s: %s", self.name, e)
            raise

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        _LOGGER.debug("Turning off light %s (where=%s)", self.name, self._where)
        
        frame = f"*1*0*{self._where}##"
        _LOGGER.debug("Sending frame: %s", frame)
        
        try:
            await self.coordinator.async_send_message(frame)
            self._attr_is_on = False
            self.async_write_ha_state()
        except Exception as e:
            _LOGGER.error("Failed to turn off light %s: %s", self.name, e)
            raise