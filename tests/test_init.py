"""End to end: mapped sensors are converted, uploaded and reported."""

from __future__ import annotations

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.ecowitt_uploader.const import CONF_INTERVAL, CONF_MAC, DOMAIN
from custom_components.ecowitt_uploader.uploader import UPLOAD_URL

from .conftest import MAC, PASSKEY

OK = '{"errcode":"0","errmsg":"ok"}'

STATES = {
    "sensor.temp": ("19.0", "°C"),
    "sensor.pressure": ("1002.6", "hPa"),
    "sensor.wind": ("27.0", "km/h"),
    "sensor.gust": ("31.68", "%"),  # wrong unit: skipped
    "sensor.solar": ("3830", "lx"),
    "sensor.rain": ("16.2", "mm"),
    "sensor.rain_rate": ("2.54", "mm/h"),
    "sensor.uv": ("0.0", None),
    "sensor.humidity": ("unavailable", "%"),
}
OPTIONS = {
    CONF_INTERVAL: 60,
    "temperature": "sensor.temp",
    "pressure_absolute": "sensor.pressure",
    "wind_speed": "sensor.wind",
    "wind_gust": "sensor.gust",
    "solar_radiation": "sensor.solar",
    "rain_daily": "sensor.rain",
    "rain_rate": "sensor.rain_rate",
    "uv_index": "sensor.uv",
    "humidity": "sensor.humidity",
    "indoor_humidity": "sensor.missing",
}


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    for entity_id, (state, unit) in STATES.items():
        hass.states.async_set(entity_id, state, {ATTR_UNIT_OF_MEASUREMENT: unit} if unit else {})
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Ecowitt.net {MAC}",
        unique_id=MAC,
        data={CONF_MAC: MAC},
        options=OPTIONS,
    )
    entry.add_to_hass(hass)
    return entry


async def test_upload_converts_and_reports(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    hass.config.elevation = 0
    aioclient_mock.post(UPLOAD_URL, text=OK)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert aioclient_mock.call_count == 1
    payload = aioclient_mock.mock_calls[0][2]
    assert payload["PASSKEY"] == PASSKEY
    assert {k: v for k, v in payload.items() if k not in {"PASSKEY", "dateutc"}} == {
        "stationtype": "HomeAssistant",
        "model": "HomeAssistant",
        "tempf": "66.2",
        "baromabsin": "29.607",
        "baromrelin": "29.607",
        "windspeedmph": "16.777",
        "solarradiation": "30.229",
        "dailyrainin": "0.638",
        "rainratein": "0.1",
        "uv": "0",
    }

    state = hass.states.get("sensor.ecowitt_net_aa_bb_cc_dd_ee_ff_last_upload")
    assert state is not None
    assert state.attributes["fields"] == [
        "baromabsin",
        "baromrelin",
        "dailyrainin",
        "rainratein",
        "solarradiation",
        "tempf",
        "uv",
        "windspeedmph",
    ]


async def test_rejected_upload_retries_setup(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(UPLOAD_URL, text='{"errcode":"-1","errmsg":"passkey error"}')

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_no_usable_sensor_does_not_upload(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    hass.states.async_set("sensor.temp", "unknown", {ATTR_UNIT_OF_MEASUREMENT: "°C"})
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=MAC, data={CONF_MAC: MAC}, options={"temperature": "sensor.temp"}
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert aioclient_mock.call_count == 0
