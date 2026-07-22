"""Gateway handler: OWNd connection, event dispatch, command queue."""
from __future__ import annotations

import asyncio
from typing import Any

from OWNd.connection import (
    OWNGateway,
    OWNSession,
    OWNEventSession,
    OWNCommandSession,
)
from OWNd.message import OWNMessage

from homeassistant.core import HomeAssistant

from .const import (
    CONF_HOST,
    CONF_MAC,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    LOGGER,
    MANUFACTURER_DEFAULT,
)

WORKER_COUNT = 1


class MyHOMEGatewayCoordinator:
    """Manages one MyHOME gateway (event listener + command sender)."""

    def __init__(self, hass: HomeAssistant, data: dict[str, Any]) -> None:
        self.hass = hass
        self._data = data
        self.mac: str = data[CONF_MAC]
        self.host: str = data[CONF_HOST]
        self.port: int = data[CONF_PORT]

        build_info = {
            "address": data[CONF_HOST],
            "port": data[CONF_PORT],
            "password": data.get(CONF_PASSWORD),
            "serialNumber": data[CONF_MAC],
            "modelName": "MyHOME Server",
            "modelNumber": None,
            "manufacturer": MANUFACTURER_DEFAULT,
            "deviceType": None,
            "friendlyName": data.get(CONF_NAME),
            "ssdp_location": None,
            "ssdp_st": None,
            "manufacturerURL": None,
            "UDN": None,
        }
        self.gateway = OWNGateway(build_info)

        self.hub_device_id: str | None = None
        self.is_connected = False
        self._handlers: dict[str, list] = {}
        self._send_buffer: asyncio.Queue = asyncio.Queue()
        self._stop = False
        self._listen_task: asyncio.Task | None = None
        self._send_tasks: list[asyncio.Task] = []
        self._event_session: OWNEventSession | None = None
        self._command_sessions: list[OWNCommandSession] = []

    # ---- properties ----
    @property
    def model(self) -> str:
        return self.gateway.model_name or "MyHOME Server"

    @property
    def firmware(self) -> str | None:
        return self.gateway.firmware

    @property
    def manufacturer(self) -> str:
        return self.gateway.manufacturer or MANUFACTURER_DEFAULT

    @property
    def log_id(self) -> str:
        return self.gateway.log_id

    # ---- connection test (used by config_flow and setup) ----
    async def async_test(self) -> dict | None:
        return await OWNSession(gateway=self.gateway, logger=LOGGER).test_connection()

    # ---- entity registry for dispatch ----
    def register(self, key: str, entity) -> None:
        self._handlers.setdefault(key, []).append(entity)

    def unregister(self, key: str, entity) -> None:
        bucket = self._handlers.get(key)
        if bucket and entity in bucket:
            bucket.remove(entity)

    def _dispatch(self, message) -> None:
        if not isinstance(message, OWNMessage) or not message.is_event:
            return
        key = message.entity  # f"{who}-{where}" (no interface in this setup)
        for ent in list(self._handlers.get(key, ())):
            try:
                ent.handle_event(message)
            except Exception:  # noqa: BLE001
                LOGGER.exception("Error handling event for %s", key)

    # ---- loops ----
    async def async_start(self) -> None:
        self._stop = False
        self._listen_task = asyncio.create_task(self._listening_loop())
        for i in range(WORKER_COUNT):
            self._send_tasks.append(asyncio.create_task(self._sending_loop(i)))

    async def _listening_loop(self) -> None:
        self._event_session = OWNEventSession(gateway=self.gateway, logger=LOGGER)
        # connect with retry
        while not self._stop:
            res = await self._event_session.connect()
            if res and res.get("Success"):
                break
            LOGGER.warning("%s event connect failed, retry in 5s", self.log_id)
            await asyncio.sleep(5)
        self.is_connected = True
        LOGGER.info("%s event session connected", self.log_id)
        while not self._stop:
            message = await self._event_session.get_next()
            if message is None:
                continue
            self._dispatch(message)
        self.is_connected = False

    async def _sending_loop(self, worker_id: int) -> None:
        session = OWNCommandSession(gateway=self.gateway, logger=LOGGER)
        self._command_sessions.append(session)
        while not self._stop:
            res = await session.connect()
            if res and res.get("Success"):
                break
            LOGGER.warning("%s command connect failed, retry in 5s", self.log_id)
            await asyncio.sleep(5)
        LOGGER.info("%s command worker %s connected", self.log_id, worker_id)
        while not self._stop:
            task = await self._send_buffer.get()
            if task is None:  # sentinel
                self._send_buffer.task_done()
                break
            await session.send(
                message=task["message"],
                is_status_request=task["is_status_request"],
            )
            self._send_buffer.task_done()

    # ---- public send API ----
    async def send(self, command) -> None:
        await self._send_buffer.put({"message": command, "is_status_request": False})

    async def send_status_request(self, command) -> None:
        await self._send_buffer.put({"message": command, "is_status_request": True})

    async def send_raw(self, frame: str) -> None:
        # str(frame) == frame inside OWNCommandSession.send
        await self._send_buffer.put({"message": frame, "is_status_request": False})

    # ---- shutdown ----
    async def async_close(self) -> None:
        self._stop = True
        for _ in self._send_tasks:
            await self._send_buffer.put(None)
        if self._listen_task:
            self._listen_task.cancel()
        for t in self._send_tasks:
            t.cancel()
        for s in [self._event_session, *self._command_sessions]:
            if s is not None:
                try:
                    await s.close()
                except Exception:  # noqa: BLE001
                    pass
        self._send_tasks.clear()
        self._command_sessions.clear()
