"""Config and options flow."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.const import CONF_ADDRESS
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ecowitt_uploader.const import CONF_INTERVAL, CONF_MAC, CONF_MODEL_ID, DOMAIN

from .conftest import MAC, add_bthome_sensor, service_info

BUTTON_DATA = {0x0BA9: bytes.fromhex("0101000b0100")}
DISCOVERED = "custom_components.ecowitt_uploader.config_flow.async_discovered_service_info"


@pytest.fixture(autouse=True)
def no_setup() -> Generator[None]:
    """Don't upload while testing the flow."""
    with patch("custom_components.ecowitt_uploader.async_setup_entry", return_value=True):
        yield


async def test_bluetooth_discovery(hass: HomeAssistant) -> None:
    add_bthome_sensor(hass, "temperature", "19.0", "°C")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=service_info()
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "confirm"
    assert result["description_placeholders"]["mac"] == MAC

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_MAC: MAC, CONF_MODEL_ID: 0x000B}
    assert result["options"] == {CONF_INTERVAL: 60}
    assert result["result"].unique_id == MAC


async def test_discovery_of_unsupported_device(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=service_info(BUTTON_DATA)
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "not_supported"


async def test_bthome_must_know_the_station(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=service_info()
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "bthome_missing"


async def test_already_configured(hass: HomeAssistant) -> None:
    MockConfigEntry(domain=DOMAIN, unique_id=MAC, data={CONF_MAC: MAC}).add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=service_info()
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_picks_a_supported_station(hass: HomeAssistant) -> None:
    add_bthome_sensor(hass, "temperature", "19.0", "°C")
    other = service_info(BUTTON_DATA, address="11:22:33:44:55:66")
    with patch(DISCOVERED, return_value=[service_info(), other]):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert list(result["data_schema"].schema[CONF_ADDRESS].container) == [MAC]

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_ADDRESS: MAC})
    assert result["step_id"] == "confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_without_supported_stations(hass: HomeAssistant) -> None:
    with patch(DISCOVERED, return_value=[service_info(BUTTON_DATA)]):
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_devices_found"


async def test_options_flow_sets_interval(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id=MAC,
        data={CONF_MAC: MAC, CONF_MODEL_ID: 0x000B},
        options={CONF_INTERVAL: 60},
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_INTERVAL: 300}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert entry.options == {CONF_INTERVAL: 300}
