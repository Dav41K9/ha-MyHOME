"""Constants for the BTicino MyHOME integration."""

DOMAIN = "myhome"

# Config entry keys
CONF_GATEWAY_NAME = "gateway_name"
CONF_MAC = "mac"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_PASSWORD = "password"

# Subentry keys
CONF_DEVICE_TYPE = "device_type"
CONF_WHERE = "where"
CONF_NAME = "name"
CONF_DIMMABLE = "dimmable"
CONF_ADVANCED = "advanced"
CONF_ZONE = "zone"
CONF_HEAT = "heat"
CONF_COOL = "cool"
CONF_STANDALONE = "standalone"
CONF_SENSOR_CLASS = "sensor_class"
CONF_DEVICE_CLASS = "device_class"
CONF_MANUFACTURER = "manufacturer"
CONF_MODEL = "model"

# Subentry types
SUBENTRY_LIGHT = "light"
SUBENTRY_SWITCH = "switch"
SUBENTRY_COVER = "cover"
SUBENTRY_CLIMATE = "climate"
SUBENTRY_SENSOR = "sensor"

# Platforms
PLATFORMS = ["light", "switch", "cover", "climate", "sensor", "button", "binary_sensor"]

# OWNd WHO values
WHO_LIGHTING = 1
WHO_AUTOMATION = 2
WHO_THERMOREGULATION = 4
WHO_ENERGY = 18

# Defaults
DEFAULT_PORT = 20000
DEFAULT_PASSWORD = "12345"

# Additional subentry keys
CONF_FRAME = "frame"
CONF_WHO = "who"
CONF_ON_VALUE = "on_value"
CONF_OFF_VALUE = "off_value"

# Additional subentry types
SUBENTRY_BUTTON = "button"
SUBENTRY_BINARY_SENSOR = "binary_sensor"

# YAML migration
OLD_YAML_PATH = "myhome.yaml"

# Dispatcher signal
SIGNAL_MYHOME_EVENT = "myhome_event_{mac}_{who}_{where}"

# Reconnect
RECONNECT_DELAY = 10
POLL_TIMEOUT = 3.0
