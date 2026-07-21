"""Coordinator for BTicino MyHOME gateway connection."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from OWNd.connection import OWNGateway, OWNEventSession, OWNCommandSession
from OWNd.message import OWNMessage

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    CONF_HOST,
    CONF_MAC,
    CONF_PASSWORD,
    CONF_PORT,
    DEFAULT_PASSWORD,
    DEFAULT_PORT,
    POLL_TIMEOUT,
    RECONNECT_DELAY,
    SIGNAL_MYHOME_EVENT,
)

_LOGGER = logging.getLogger(__name__)


class MyHOMEGatewayCoordinator:
    """Manage the OWNd connection to a single gateway."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.mac: str = str(entry.data.get(CONF_MAC, ""))
        self.host: str = str(entry.data.get(CONF_HOST, ""))
        self.port: int = int(entry.data.get(CONF_PORT, DEFAULT_PORT))
        self.password: str = str(entry.data.get(CONF_PASSWORD, DEFAULT_PASSWORD))

        self._gateway: OWNGateway | None = None
        self._event_session: OWNEventSession | None = None
        self._listener_task: asyncio.Task | None = None
        self._running = False
        self._connected = False

        # Pending request/response for polling
        self._pending: dict[str, asyncio.Future] = {}

    def _build_gateway(self) -> OWNGateway:
        """Build an OWNGateway instance from config entry data."""
        return OWNGateway({
            "address": self.host,
            "port": self.port,
            "password": self.password,
            "serialNumber": self.mac,
            "modelName": "MyHOME Server",
            "manufacturer": "BTicino S.p.A.",
        })

    @property
    def connected(self) -> bool:
        """Return True if connected to the gateway."""
        return self._connected

    async def async_connect(self) -> bool:
        """Test connectivity with a simple TCP check (avoids OWNd logger bug)."""
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=10,
            )
            writer.close()
            await writer.wait_closed()
            self._connected = True
            _LOGGER.info(
                "Gateway %s reachable at %s:%s",
                self.mac, self.host, self.port,
            )
            return True
        except (asyncio.TimeoutError, OSError):
            self._connected = False
            _LOGGER.warning(
                "Cannot reach gateway %s at %s:%s",
                self.mac, self.host, self.port,
            )
            return False
        except Exception:
            self._connected = False
            _LOGGER.exception(
                "Unexpected error testing gateway %s at %s:%s",
                self.mac, self.host, self.port,
            )
            return False

    async def async_start_listener(self) -> None:
        """Start the event listener as a background task tied to the entry."""
        self._running = True
        self._listener_task = self.entry.async_create_background_task(
            self.hass,
            self._listen_loop(),
            name=f"myhome-listener-{self.mac}",
        )

    async def _listen_loop(self) -> None:
        """Main listener loop with auto-reconnect."""
        while self._running:
            try:
                if self._gateway is None:
                    self._gateway = self._build_gateway()

                # Pass logger explicitly to avoid the NoneType bug
                self._event_session = OWNEventSession(
                    gateway=self._gateway,
                    logger=_LOGGER,
                )
                await self._event_session.connect()
                self._connected = True
                _LOGGER.info(
                    "Event session started for gateway %s", self.mac
                )

                while self._running:
                    message = await self._event_session.get_next()
                    if message is None:
                        continue
                    if isinstance(message, OWNMessage):
                        self._handle_message(message)

            except asyncio.CancelledError:
                break
            except Exception:
                if self._running:
                    _LOGGER.warning(
                        "Connection to gateway %s lost, reconnecting in %ss...",
                        self.mac, RECONNECT_DELAY,
                    )
                self._connected = False
                if self._event_session:
                    try:
                        await self._event_session.close()
                    except Exception:
                        pass
                    self._event_session = None
                if self._running:
                    await asyncio.sleep(RECONNECT_DELAY)

    @callback
    def _handle_message(self, message: OWNMessage) -> None:
        """Dispatch an incoming OWNd message to entities and pending requests."""
        who = getattr(message, "who", None)
        where = getattr(message, "where", None)

        if who is None or where is None:
            return

        who_str = str(who)
        where_str = str(where)

        # Resolve pending polling requests
        pending_key = f"{who_str}_{where_str}"
        if pending_key in self._pending:
            future = self._pending.pop(pending_key)
            if not future.done():
                future.set_result(message)

        # Dispatch to entities
        signal = SIGNAL_MYHOME_EVENT.format(
            mac=self.mac, who=who_str, where=where_str
        )
        async_dispatcher_send(self.hass, signal, message)

    async def async_send_message(self, message: str) -> None:
        """Send a raw OpenWebNet frame to the gateway."""
        if not self._gateway:
            self._gateway = self._build_gateway()

        try:
            await OWNCommandSession.send_to_gateway(
                message=message,
                gateway=self._gateway,
            )
        except Exception:
            _LOGGER.debug(
                "Could not send message `%s` to gateway %s",
                message, self.mac,
            )

    async def async_request_state(
        self, who: int, where: str, timeout: float = POLL_TIMEOUT
    ) -> OWNMessage | None:
        """Send a state request (*#WHO*WHERE##) and wait for the response."""
        if not self._connected:
            return None

        pending_key = f"{who}_{where}"
        frame = f"*#{who}*{where}##"

        loop = asyncio.get_running_loop()
        future: asyncio.Future[OWNMessage] = loop.create_future()
        self._pending[pending_key] = future

        try:
            await self.async_send_message(frame)
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            _LOGGER.debug(
                "State request `%s` timed out for gateway %s",
                frame, self.mac,
            )
            return None
        except Exception:
            _LOGGER.debug(
                "State request `%s` failed for gateway %s",
                frame, self.mac,
            )
            return None
        finally:
            self._pending.pop(pending_key, None)

    async def async_disconnect(self) -> None:
        """Stop listener and disconnect."""
        self._running = False

        for future in self._pending.values():
            if not future.done():
                future.cancel()
        self._pending.clear()

        if self._listener_task and not self._listener_task.done():
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass

        if self._event_session:
            try:
                await self._event_session.close()
            except Exception:
                pass
            self._event_session = None

        self._connected = False
        _LOGGER.info("Disconnected from gateway %s", self.mac)
