"""Constants for the BTicino MyHOME integration."""
from __future__ import annotations

import logging

from homeassistant.const import Platform

DOMAIN = "myhome"

# --- config entry (hub) keys ---
CONF_HOST = "host"
CONF_PORT = "port"
CONF_PASSWORD = "password"
CONF_MAC = "mac"
CONF_NAME = "name"

# --- subentry (device) keys ---
CONF_WHERE = "where"
CONF_DIMMABLE = "dimmable"
CONF_ADVANCED = "advanced"
CONF_DEVICE_CLASS = "device_class"
CONF_HEAT = "heat"
CONF_COOL = "cool"
CONF_STANDALONE = "standalone"
CONF_MANUFACTURER = "manufacturer"
CONF_MODEL = "model"
CONF_INVERTED = "inverted"
CONF_WHO = "who"

# --- subentry types (== platform names) ---
SUBENTRY_LIGHT = "light"
SUBENTRY_SWITCH = "switch"
SUBENTRY_COVER = "cover"
SUBENTRY_CLIMATE = "climate"
SUBENTRY_SENSOR = "sensor"
SUBENTRY_BINARY_SENSOR = "binary_sensor"

PLATFORMS = [
    Platform.LIGHT,
    Platform.SWITCH,
    Platform.COVER,
    Platform.CLIMATE,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]

# --- defaults ---
DEFAULT_PORT = 20000
DEFAULT_PASSWORD = "12345"
DEFAULT_NAME = "MyHOME"
MANUFACTURER_DEFAULT = "BTicino S.p.A."

# --- services ---
SERVICE_SYNC_TIME = "sync_time"
SERVICE_SEND_MESSAGE = "send_message"
SERVICE_IMPORT_YAML = "import_yaml"
SERVICE_START_INSTANT_POWER = "start_sending_instant_power"

OLD_YAML_PATH = "/config/myhome.yaml"

LOGGER = logging.getLogger("custom_components.myhome")
