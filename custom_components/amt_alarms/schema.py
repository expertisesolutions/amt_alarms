
import voluptuous as vol
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_AWAY_MODE_ENABLED,
    CONF_AWAY_PARTITION_1,
    CONF_AWAY_PARTITION_2,
    CONF_AWAY_PARTITION_3,
    CONF_AWAY_PARTITION_4,
    CONF_HOME_MODE_ENABLED,
    CONF_HOME_PARTITION_1,
    CONF_HOME_PARTITION_2,
    CONF_HOME_PARTITION_3,
    CONF_HOME_PARTITION_4,
    CONF_NIGHT_PARTITION_1,
    CONF_NIGHT_PARTITION_2,
    CONF_NIGHT_PARTITION_3,
    CONF_NIGHT_PARTITION_4,
    CONF_PASSWORD,
    CONF_PORT,
    DOMAIN,  # PARTITION_LIST,; pylint:disable=unused-import
)

partition_on = "Active"
partition_off = "Not active"
partition_none = "Don't care"
partition_vol = vol.In([partition_none, partition_on, partition_off])

user_schema = {
    vol.Required(CONF_PORT, default=9009): cv.port,
    CONF_PASSWORD: int,
}
night_partition_schema = {
    vol.Required(CONF_NIGHT_PARTITION_1, default=partition_on): partition_vol,
    vol.Required(CONF_NIGHT_PARTITION_2, default=partition_on): partition_vol,
    vol.Required(CONF_NIGHT_PARTITION_3, default=partition_on): partition_vol,
    vol.Required(CONF_NIGHT_PARTITION_4, default=partition_on): partition_vol,
}
away_mode_partition_schema = {
    vol.Required(CONF_AWAY_MODE_ENABLED, default=False): bool,
    vol.Required(CONF_AWAY_PARTITION_1, default=partition_on): partition_vol,
    vol.Required(CONF_AWAY_PARTITION_2, default=partition_on): partition_vol,
    vol.Required(CONF_AWAY_PARTITION_3, default=partition_on): partition_vol,
    vol.Required(CONF_AWAY_PARTITION_4, default=partition_on): partition_vol,
}
home_mode_partition_schema = {
    vol.Required(CONF_HOME_MODE_ENABLED, default=False): bool,
    vol.Required(CONF_HOME_PARTITION_1, default=partition_none): partition_vol,
    vol.Required(CONF_HOME_PARTITION_2, default=partition_none): partition_vol,
    vol.Required(CONF_HOME_PARTITION_3, default=partition_none): partition_vol,
    vol.Required(CONF_HOME_PARTITION_4, default=partition_none): partition_vol,
}
