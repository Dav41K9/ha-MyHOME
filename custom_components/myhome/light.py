"""Lights (WHO 1)."""
from __future__ import annotations

from OWNd.message import OWNLightingCommand, OWNLightingEvent
from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_FLASH,
    ATTR_TRANSITION,
    FLASH_SHORT,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_DIMMABLE,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_NAME,
    CONF_WHERE,
    OPTIONS_DEVICES,
    SUBENTRY_LIGHT,
)
from .entity import MyHOMEEntity


def _pct_to_8b(v: int) -> int:
    return int(round(255 / 100 * v, 0))


def _8b_to_pct(v: int) -> int:
    return int(round(100 / 255 * v, 0))


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = entry.runtime_data
    entities = [
        MyHOMELight(coord, dev["id"], dev)
        for dev in entry.options.get(OPTIONS_DEVICES, [])
        if dev.get("type") == SUBENTRY_LIGHT
    ]
    async_add_entities(entities)


class MyHOMELight(MyHOMEEntity, LightEntity):
    def __init__(self, coordinator, device_id: str, data: dict) -> None:
        super().__init__(
            coordinator,
            device_id,
            who=1,
            where=data[CONF_WHERE],
            name=data[CONF_NAME],
            manufacturer=data.get(CONF_MANUFACTURER, ""),
            model=data.get(CONF_MODEL, ""),
        )
        self._dimmable = bool(data.get(CONF_DIMMABLE, False))
        if self._dimmable:
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_features = LightEntityFeature.TRANSITION
        else:
            self._attr_supported_color_modes = {ColorMode.ONOFF}
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_features = LightEntityFeature.FLASH
        self._attr_is_on = None
        self._attr_brightness = None

    async def async_request_initial_state(self) -> None:
        cmd = (
            OWNLightingCommand.get_brightness(self._where)
            if self._dimmable
            else OWNLightingCommand.status(self._where)
        )
        await self._coordinator.send_status_request(cmd)

    async def async_turn_on(self, **kwargs) -> None:
        if ATTR_FLASH in kwargs and LightEntityFeature.FLASH in self._attr_supported_features:
            freq = 0.5 if kwargs[ATTR_FLASH] == FLASH_SHORT else 1.5
            return await self._coordinator.send(OWNLightingCommand.flash(self._where, freq))
        if (ATTR_BRIGHTNESS in kwargs and ColorMode.BRIGHTNESS in self._attr_supported_color_modes) or (
            ATTR_TRANSITION in kwargs and LightEntityFeature.TRANSITION in self._attr_supported_features
        ):
            pct = _8b_to_pct(kwargs[ATTR_BRIGHTNESS]) if ATTR_BRIGHTNESS in kwargs else 30
            tr = int(kwargs[ATTR_TRANSITION]) if ATTR_TRANSITION in kwargs else 0
            if pct == 0:
                return await self.async_turn_off(**kwargs)
            await self._coordinator.send(OWNLightingCommand.set_brightness(self._where, pct, tr))
        else:
            tr = int(kwargs[ATTR_TRANSITION]) if ATTR_TRANSITION in kwargs else None
            await self._coordinator.send(OWNLightingCommand.switch_on(self._where, tr))
        if self._dimmable:
            await self.async_request_initial_state()

    async def async_turn_off(self, **kwargs) -> None:
        tr = int(kwargs[ATTR_TRANSITION]) if ATTR_TRANSITION in kwargs else None
        await self._coordinator.send(OWNLightingCommand.switch_off(self._where, tr))

    def handle_event(self, message: OWNLightingEvent) -> None:
        self._attr_is_on = message.is_on
        if self._dimmable and message.brightness is not None:
            self._attr_brightness = _pct_to_8b(message.brightness)
        self.async_write_ha_state()
