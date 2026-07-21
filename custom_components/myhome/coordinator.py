"""Coordinator for BTicino MyHOME integration."""
from __future__ import annotations

import logging
from typing import Any

from OWNd import OWNError, OWNException
from OWNd.command import OWNCommandSession
from OWNd.gateway import OWNGateway
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)

class MyHOMEGatewayCoordinator(DataUpdateCoordinator):
    """Coordinator for BTicino MyHOME gateway."""

    def __init__(self, hass: HomeAssistant, entry: dict[str, Any]) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=None,  # Non usiamo polling
        )
        self.host = entry[CONF_HOST]
        self.port = entry.get(CONF_PORT, DEFAULT_PORT)
        self.mac = entry["unique_id"]
        self._gateway: OWNGateway | None = None
        self._connected = False
        self._devices: dict[str, dict] = {}

    async def async_connect(self) -> bool:
        """Connect to the gateway."""
        try:
            self._gateway = OWNGateway(host=self.host, port=self.port)
            await self._gateway.connect()
            self._connected = True
            _LOGGER.info("Connected to BTicino gateway at %s:%s", self.host, self.port)
            return True
        except OWNException as exc:
            _LOGGER.error("Failed to connect to gateway: %s", exc)
            return False

    async def async_disconnect(self) -> None:
        """Disconnect from the gateway."""
        if self._gateway:
            try:
                await self._gateway.disconnect()
                _LOGGER.info("Disconnected from BTicino gateway")
            except Exception as exc:
                _LOGGER.error("Error disconnecting from gateway: %s", exc)
            finally:
                self._gateway = None
                self._connected = False

    async def async_start_listener(self) -> None:
        """Start listening for incoming messages."""
        if not self._gateway:
            _LOGGER.error("Gateway not connected, cannot start listener")
            return

        async def _handle_message(message: str) -> None:
            """Handle incoming OpenWebNet message."""
            _LOGGER.debug("Received message: %s", message)
            # Qui elabora i messaggi e aggiorna lo stato
            self.async_set_updated_data(self._devices)

        try:
            await OWNCommandSession.start_listening(
                gateway=self._gateway,
                callback=_handle_message,
            )
        except OWNException as exc:
            _LOGGER.error("Failed to start listener: %s", exc)

    async def async_send_message(self, message: str) -> None:
        """Send a raw OpenWebNet frame to the gateway."""
        if not self._gateway:
            self._gateway = await self._build_gateway()
        
        try:
            if not self._connected:
                _LOGGER.warning("Gateway not connected, attempting to reconnect...")
                await self.async_connect()
            
            await OWNCommandSession.send_to_gateway(
                message=message,
                gateway=self._gateway,
                timeout=5.0,
            )
            _LOGGER.debug("Message sent successfully: %s", message)
        except Exception as e:
            _LOGGER.error(
                "Failed to send message '%s' to gateway %s: %s",
                message, self.mac, e
            )
            raise

    async def _build_gateway(self) -> OWNGateway:
        """Build and connect gateway."""
        gateway = OWNGateway(host=self.host, port=self.port)
        await gateway.connect()
        self._connected = True
        return gateway