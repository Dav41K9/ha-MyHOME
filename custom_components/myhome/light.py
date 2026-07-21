"""Light platform for BTicino MyHOME."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ColorMode,
    LightEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_DIMMABLE,
    CONF_WHERE,
    SUBENTRY_LIGHT,
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
    """Set up MyHOME lights from config entry subentries."""
    coordinator: MyHOMEGatewayCoordinator = entry.runtime_data

    entities = []
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type == SUBENTRY_LIGHT:
            entities.append(
                MyHOMELight(coordinator, entry, subentry_id, subentry.data)
            )

    async_add_entities(entities)


class MyHOMELight(MyHOMEEntity, LightEntity):
    """Representation of a MyHOME light."""

    def __init__(self, coordinator, entry, subentry_id, data) -> None:
        super().__init__(coordinator, entry, subentry_id, data)
        self._dimmable = bool(data.get(CONF_DIMMABLE, False))
        self._attr_is_on = False
        self._attr_brightness = 255

        if self._dimmable:
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        else:
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_color_modes = {ColorMode.ONOFF}

    def _get_who(self) -> int:
        return WHO_LIGHTING

    async def _async_request_initial_state(self) -> None:
        """Request initial light state from the gateway."""
        message = await self._coordinator.async_request_state(
            WHO_LIGHTING, self._where
        )
        if message:
            self._parse_state(message)

    @callback
    def _handle_event(self, message) -> None:
        """Handle light state change from bus."""
        self._parse_state(message)
        self.async_write_ha_state()

    @callback
    def _parse_state(self, message) -> None:
        """Parse an OWNd light message."""
        try:
            what = str(getattr(message, "what", ""))
            if not what:
                return

            # *1*WHERE*1## = ON, *1*WHERE*0## = OFF
            # *1*WHERE*1*LEVEL## = dimmer
            if what == "1":
                self._attr_is_on = True
            elif what == "0":
                self._attr_is_on = False
            elif what.startswith("1"):
                self._attr_is_on = True
                parts = what.split("*")
                if len(parts) >= 2:
                    try:
                        level = int(parts[-1])
                        self._attr_brightness = max(
                            0, min(255, int(level * 255 / 100))
                        )
                    except ValueError:
                        pass
        except Exception:
            _LOGGER.debug(
                "Error parsing light event for %s", self._where, exc_info=True
            )

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        if ATTR_BRIGHTNESS in kwargs and self._dimmable:
            brightness = kwargs[ATTR_BRIGHTNESS]
            level = max(1, min(100, int(brightness * 100 / 255)))
            await self._coordinator.async_send_message(
                f"*1*1*{self._where}*{level}##"
            )
            self._attr_brightness = brightness
        else:
            await self._coordinator.async_send_message(
                f"*1*1*{self._where}##"
            )
        self._attr_is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        await self._coordinator.async_send_message(
            f"*1*0*{self._where}##"
        )
        self._attr_is_on = False
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict:
        """Return A/PL breakdown."""
        where = self._where
        if len(where) > 2:
            mid = len(where) // 2
            return {"A": where[:mid], "PL": where[mid:]}
        return {"PL": where}
