"""Constants for the Ecowitt.net Uploader integration."""

from __future__ import annotations

from typing import Final, NamedTuple

from homeassistant.const import (
    UnitOfIrradiance,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
    UnitOfVolumetricFlux,
)

DOMAIN: Final = "ecowitt_uploader"

CONF_MAC: Final = "mac"
CONF_INTERVAL: Final = "interval"

DEFAULT_INTERVAL: Final = 60
MIN_INTERVAL: Final = 30
MAX_INTERVAL: Final = 600


class Field(NamedTuple):
    """A measurement the user can map to a Home Assistant sensor."""

    key: str  # config option key, also the translation key
    param: str  # Ecowitt protocol parameter
    unit: str | None  # unit the protocol expects; None = sent as-is


FIELDS: Final[tuple[Field, ...]] = (
    Field("temperature", "tempf", UnitOfTemperature.FAHRENHEIT),
    Field("humidity", "humidity", None),
    Field("pressure_absolute", "baromabsin", UnitOfPressure.INHG),
    Field("pressure_relative", "baromrelin", UnitOfPressure.INHG),
    Field("wind_speed", "windspeedmph", UnitOfSpeed.MILES_PER_HOUR),
    Field("wind_gust", "windgustmph", UnitOfSpeed.MILES_PER_HOUR),
    Field("wind_direction", "winddir", None),
    Field("rain_rate", "rainratein", UnitOfVolumetricFlux.INCHES_PER_HOUR),
    Field("rain_event", "eventrainin", UnitOfPrecipitationDepth.INCHES),
    Field("rain_hourly", "hourlyrainin", UnitOfPrecipitationDepth.INCHES),
    Field("rain_daily", "dailyrainin", UnitOfPrecipitationDepth.INCHES),
    Field("rain_weekly", "weeklyrainin", UnitOfPrecipitationDepth.INCHES),
    Field("rain_monthly", "monthlyrainin", UnitOfPrecipitationDepth.INCHES),
    Field("rain_yearly", "yearlyrainin", UnitOfPrecipitationDepth.INCHES),
    Field("solar_radiation", "solarradiation", UnitOfIrradiance.WATTS_PER_SQUARE_METER),
    Field("uv_index", "uv", None),
    Field("indoor_temperature", "tempinf", UnitOfTemperature.FAHRENHEIT),
    Field("indoor_humidity", "humidityin", None),
)
