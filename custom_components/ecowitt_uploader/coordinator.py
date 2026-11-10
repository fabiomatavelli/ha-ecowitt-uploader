"""Periodic upload of a supported station's BTHome readings to Ecowitt.net."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    LIGHT_LUX,
    UnitOfIrradiance,
    UnitOfPrecipitationDepth,
    UnitOfPressure,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import (
    BaseUnitConverter,
    DistanceConverter,
    PressureConverter,
    SpeedConverter,
    TemperatureConverter,
)

from .const import CONF_INTERVAL, CONF_MAC, CONF_MODEL_ID, DEFAULT_INTERVAL, DOMAIN, PARAM_UNITS
from .profiles import PROFILES
from .rain import RainTracker
from .uploader import UploadError, async_upload, build_payload

_LOGGER = logging.getLogger(__name__)

# Ecowitt.net shows solar radiation as lux using this factor, so it's the one to undo.
LUX_PER_W_M2 = 126.7

IDENTITY_PARAMS = {"PASSKEY", "stationtype", "model", "dateutc"}

CONVERTERS: dict[str, type[BaseUnitConverter]] = {
    UnitOfTemperature.FAHRENHEIT: TemperatureConverter,
    UnitOfPressure.INHG: PressureConverter,
    UnitOfSpeed.MILES_PER_HOUR: SpeedConverter,
    UnitOfPrecipitationDepth.INCHES: DistanceConverter,
}


@dataclass(frozen=True)
class UploadStatus:
    """Result of the last successful upload."""

    uploaded_at: datetime
    params: list[str]


def convert(value: float, from_unit: str | None, to_unit: str | None) -> float | None:
    """Convert to the protocol's unit, or None if the source unit isn't usable."""
    if to_unit is None:
        return value
    if to_unit == UnitOfIrradiance.WATTS_PER_SQUARE_METER:
        if from_unit == LIGHT_LUX:
            return value / LUX_PER_W_M2
        return value if from_unit == to_unit else None
    converter = CONVERTERS[to_unit]
    if from_unit not in converter.VALID_UNITS:
        return None
    return converter.convert(value, from_unit, to_unit)


type EcowittUploaderConfigEntry = ConfigEntry[EcowittUploadCoordinator]


class EcowittUploadCoordinator(DataUpdateCoordinator[UploadStatus]):
    """Reads the station's BTHome entities and uploads them every ``interval`` seconds."""

    config_entry: EcowittUploaderConfigEntry

    def __init__(self, hass: HomeAssistant, entry: EcowittUploaderConfigEntry) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
        )
        self._session = async_get_clientsession(hass)
        self.profile = PROFILES[entry.data[CONF_MODEL_ID]]
        self.rain = RainTracker(hass, entry.entry_id) if self.profile.rain_total else None

    async def _async_setup(self) -> None:
        if self.rain:
            await self.rain.async_load()

    async def async_shutdown(self) -> None:
        """On unload, flush the rain state so no delayed write outlives the entry."""
        await super().async_shutdown()
        if self.rain:
            await self.rain.async_save()

    def _state(self, key: str) -> State | None:
        """State of the station's BTHome sensor ``key``."""
        unique_id = f"{self.config_entry.data[CONF_MAC]}-{key}"
        entity_id = er.async_get(self.hass).async_get_entity_id("sensor", "bthome", unique_id)
        return self.hass.states.get(entity_id) if entity_id else None

    def _value(self, key: str, unit: str | None) -> float | None:
        """Current value of BTHome sensor ``key`` in ``unit``, or None if unusable."""
        state = self._state(key)
        if state is None:
            return None
        try:
            raw = float(state.state)
        except ValueError:  # unknown / unavailable
            return None
        value = convert(raw, state.attributes.get(ATTR_UNIT_OF_MEASUREMENT), unit)
        if value is None:
            _LOGGER.debug("Skipping %s: unit can't be converted", state.entity_id)
        return value

    def read_values(self) -> dict[str, float]:
        """Current readings in protocol units, keyed by Ecowitt parameter."""
        values: dict[str, float] = {}
        for key, param in self.profile.sensors.items():
            if (value := self._value(key, PARAM_UNITS[param])) is not None:
                values[param] = value
        if self.rain and self.profile.rain_total:
            total = self._value(self.profile.rain_total, UnitOfPrecipitationDepth.INCHES)
            if total is not None:
                values.update(self.rain.update(total, dt_util.now()))
        return values

    async def _async_update_data(self) -> UploadStatus:
        values = self.read_values()
        if not values:
            raise UpdateFailed("The station has no usable readings yet")
        now = dt_util.utcnow()
        payload = build_payload(
            self.config_entry.data[CONF_MAC], values, now, self.hass.config.elevation
        )
        try:
            await async_upload(self._session, payload)
        except UploadError as err:
            raise UpdateFailed(str(err)) from err
        return UploadStatus(uploaded_at=now, params=sorted(payload.keys() - IDENTITY_PARAMS))
