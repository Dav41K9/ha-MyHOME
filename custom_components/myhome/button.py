"""Button platform for BTicino MyHOME (scenarios / custom frames)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_FRAME,
    CONF_MANUFACTURER,
    CONF_MODEL,
    CONF_NAME,
    CONF_WHERE,
    CONF_WHO,
    LOGGER,
    OPTIONS_DEVICES,
    SUBENTRY_BUTTON,
)
from .entity import MyHOMEEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coord = entry.runtime_data
    async_add_entities(
        MyHOMEButton(coord, dev["id"], dev)
        for dev in entry.options.get(OPTIONS_DEVICES, [])
        if dev.get("type") == SUBENTRY_BUTTON
    )


class MyHOMEButton(MyHOMEEntity, ButtonEntity):
    """A button that sends an OpenWebNet frame (e.g. to trigger a scenario)."""

    def __init__(self, coordinator, device_id: str, data: dict) -> None:
        super().__init__(
            coordinator,
            device_id,
            who=int(data.get(CONF_WHO, 0)),
            where=str(data.get(CONF_WHERE, "")),
            name=data.get(CONF_NAME, "Button"),
            manufacturer=data.get(CONF_MANUFACTURER, ""),
            model=data.get(CONF_MODEL, ""),
        )
        # If a custom frame is provided, use it; otherwise build *WHO*WHERE##
        custom = str(data.get(CONF_FRAME, "")).strip()
        if custom:
            self._frame = custom
        elif self._where:
            self._frame = f"*{self._who}*{self._where}##"
        else:
            self._frame = ""
            LOGGER.warning(
                "Button '%s' has no frame and no where address; it will do nothing.",
                self._attr_name or device_id,
            )

    async def async_press(self) -> None:
        """Send the configured OpenWebNet frame to the gateway."""
        if not self._frame:
            LOGGER.warning("Button '%s' pressed but has no frame to send.", self._attr_name)
            return
        await self._coordinator.send_raw(self._frame)
        LOGGER.debug("Button '%s' sent frame `%s`", self._attr_name, self._frame)

    def handle_event(self, message) -> None:
        """Buttons do not react to bus events; ignore them."""
        pass
