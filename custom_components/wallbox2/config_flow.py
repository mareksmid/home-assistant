from homeassistant.config_entries import ConfigFlow

from homeassistant.components.wallbox.config_flow import STEP_USER_DATA_SCHEMA as ORIG_STEP_USER_DATA_SCHEMA, WallboxConfigFlow
from .const import DOMAIN

COMPONENT_DOMAIN = DOMAIN

STEP_USER_DATA_SCHEMA = ORIG_STEP_USER_DATA_SCHEMA


class Wallbox2ConfigFlow(WallboxConfigFlow, ConfigFlow, domain=COMPONENT_DOMAIN):
    pass
