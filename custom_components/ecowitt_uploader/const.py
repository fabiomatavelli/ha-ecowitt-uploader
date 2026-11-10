"""Constants for the Ecowitt.net Uploader integration."""

from __future__ import annotations

from typing import Final

from homeassistant.const import (
    UnitOfIrradiance,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)

DOMAIN: Final = "ecowitt_uploader"

CONF_MAC: Final = "mac"
CONF_MODEL_ID: Final = "model_id"
CONF_INTERVAL: Final = "interval"

DEFAULT_INTERVAL: Final = 60
MIN_INTERVAL: Final = 30
MAX_INTERVAL: Final = 600

# Unit each Ecowitt protocol parameter is sent in; None = sent as-is.
PARAM_UNITS: Final[dict[str, str | None]] = {
    "tempf": UnitOfTemperature.FAHRENHEIT,
    "humidity": None,
    "baromabsin": UnitOfPressure.INHG,
    "windspeedmph": UnitOfSpeed.MILES_PER_HOUR,
    "windgustmph": UnitOfSpeed.MILES_PER_HOUR,
    "winddir": None,
    "uv": None,
    "solarradiation": UnitOfIrradiance.WATTS_PER_SQUARE_METER,
}
