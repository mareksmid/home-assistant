from enum import StrEnum

DOMAIN = "wallbox2"
UPDATE_INTERVAL = 120

CONF_STATION = "station"

SESSIONS_DATA = "data"
SESSION_ATTRIBUTES = "attributes"
SESSION_ENERGY = "energy"
SESSION_TIME = "start_time"
CHARGER_GROUP_ID = "group_id"

CHARGER_DATA_POST_L1_KEY = "data"
CHARGER_DATA_POST_L2_KEY = "chargerData"

CHARGER_ADDED_GREEN_ENERGY_KEY = "added_green_energy"
CHARGER_ADDED_GRID_ENERGY_KEY = "added_grid_energy"


CHARGER_MAX_CHARGING_CURRENT_POST_KEY = "maxChargingCurrent"
# CHARGER_MAX_ICP_CURRENT_KEY = "icp_max_current"
CHARGER_MAX_ICP_CURRENT_POST_KEY = "maxAvailableCurrent"


CHARGER_ECO_SMART_KEY = "ecosmart"
CHARGER_ECO_SMART_STATUS_KEY = "enabled"
CHARGER_ECO_SMART_MODE_KEY = "mode"

CHARGER_WALLBOX_OBJECT_KEY = "wallbox"

CHARGER_JWT_TOKEN = "jwtToken"
CHARGER_JWT_REFRESH_TOKEN = "jwtRefreshToken"
CHARGER_JWT_TTL = "jwtTokenTtl"
CHARGER_JWT_REFRESH_TTL = "jwtRefreshTokenTtl"


DISABLED = "disabled"

class EcoSmartMode(StrEnum):
    """Charger Eco mode select options."""

    OFF = "off"
    ECO_MODE = "eco_mode"
    FULL_SOLAR = "full_solar"
    DISABLED = "disabled"
