"""End to end: the station's BTHome readings are converted, uploaded and reported."""

from __future__ import annotations

from datetime import timedelta

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.ecowitt_uploader.const import CONF_INTERVAL, CONF_MAC, CONF_MODEL_ID, DOMAIN
from custom_components.ecowitt_uploader.uploader import UPLOAD_URL

from .conftest import MAC, PASSKEY, add_bthome_sensor

OK = '{"errcode":"0","errmsg":"ok"}'

# Units as a WS90 shows up in Home Assistant (wind switched to km/h by the user).
WS90_STATES = {
    "temperature": ("19.0", "°C"),
    "humidity": ("90", "%"),
    "pressure": ("1002.6", "hPa"),
    "speed_1": ("27.0", "km/h"),
    "speed_2": ("31.68", "km/h"),
    "direction": ("225.0", "°"),
    "uv_index": ("0.0", None),
    "illuminance": ("3830", "lx"),
    "precipitation": ("44.5", "mm"),
    "dew_point": ("17.3", "°C"),  # not uploaded: Ecowitt.net computes it
}


@pytest.fixture
def entry(hass: HomeAssistant) -> MockConfigEntry:
    for key, (state, unit) in WS90_STATES.items():
        add_bthome_sensor(hass, key, state, unit)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=f"Ecowitt.net {MAC}",
        unique_id=MAC,
        data={CONF_MAC: MAC, CONF_MODEL_ID: 0x000B},
        options={CONF_INTERVAL: 60},
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
        "humidity": "90",
        "baromabsin": "29.607",
        "baromrelin": "29.607",
        "windspeedmph": "16.777",
        "windgustmph": "19.685",
        "winddir": "225",
        "uv": "0",
        "solarradiation": "30.229",
        # first reading after install: every period starts at zero
        "dailyrainin": "0",
        "weeklyrainin": "0",
        "monthlyrainin": "0",
        "yearlyrainin": "0",
        "rainratein": "0",
    }

    state = hass.states.get("sensor.ecowitt_net_aa_bb_cc_dd_ee_ff_last_upload")
    assert state is not None
    assert "dailyrainin" in state.attributes["fields"]


async def test_rain_since_setup_is_uploaded(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(UPLOAD_URL, text=OK)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    add_bthome_sensor(hass, "precipitation", "47.04", "mm")  # +2.54 mm = 0.1 in
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()

    assert aioclient_mock.call_count == 2
    assert aioclient_mock.mock_calls[1][2]["dailyrainin"] == "0.1"


async def test_keeps_uploading_with_status_sensor_disabled(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    er.async_get(hass).async_get_or_create(
        "sensor",
        DOMAIN,
        f"{MAC}_last_upload",
        config_entry=entry,
        disabled_by=er.RegistryEntryDisabler.USER,
    )
    aioclient_mock.post(UPLOAD_URL, text=OK)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == 1

    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=61))
    await hass.async_block_till_done()
    assert aioclient_mock.call_count == 2


async def test_removing_entry_deletes_rain_state(
    hass: HomeAssistant,
    entry: MockConfigEntry,
    aioclient_mock: AiohttpClientMocker,
    hass_storage: dict,
) -> None:
    key = f"{DOMAIN}.{entry.entry_id}.rain"
    hass_storage[key] = {
        "version": 1,
        "key": key,
        "data": {"offset": 0.0, "last_total": None, "bases": {}},
    }
    aioclient_mock.post(UPLOAD_URL, text=OK)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert key not in hass_storage

    # the upload above scheduled a delayed save: it must not bring the file back
    async_fire_time_changed(hass, dt_util.utcnow() + timedelta(seconds=60))
    await hass.async_block_till_done()
    assert key not in hass_storage


async def test_rejected_upload_retries_setup(
    hass: HomeAssistant, entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    aioclient_mock.post(UPLOAD_URL, text='{"errcode":"-1","errmsg":"passkey error"}')

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_station_without_readings_does_not_upload(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    add_bthome_sensor(hass, "temperature", "unknown", "°C")
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=MAC, data={CONF_MAC: MAC, CONF_MODEL_ID: 0x000B}, options={}
    )
    entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(entry.entry_id)
    assert entry.state is ConfigEntryState.SETUP_RETRY
    assert aioclient_mock.call_count == 0
