"""Shared pytest fixtures for the Ecowitt.net Uploader test suite."""

from __future__ import annotations

import pytest
from habluetooth import BluetoothServiceInfo
from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

pytest_plugins = "pytest_homeassistant_custom_component"

MAC = "AA:BB:CC:DD:EE:FF"
# upper(md5(MAC)), computed independently
PASSKEY = "6393CFC4AB6D416690B21278957AEAB2"

# Shelly manufacturer data as broadcast by a WS90 (SBWS-90CM): flags, model 0x000B, MAC.
WS90_MANUFACTURER_DATA = {0x0BA9: bytes.fromhex("0101000b0b000a") + bytes.fromhex("ffeeddccbbaa")}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Make custom_components discoverable in every test."""


@pytest.fixture(autouse=True)
def auto_mock_bluetooth(mock_bluetooth: None) -> None:
    """The integration depends on bluetooth: mock the adapters and scanner."""


def service_info(
    manufacturer_data: dict[int, bytes] = WS90_MANUFACTURER_DATA, address: str = MAC
) -> BluetoothServiceInfo:
    """A Bluetooth advertisement as Home Assistant reports it."""
    return BluetoothServiceInfo(
        name="SBWS-90CM",
        address=address,
        rssi=-60,
        manufacturer_data=manufacturer_data,
        service_data={},
        service_uuids=[],
        source="local",
    )


def add_bthome_sensor(
    hass: HomeAssistant, key: str, state: str, unit: str | None, mac: str = MAC
) -> str:
    """Register a BTHome sensor ``<mac>-<key>`` and give it a state, like BTHome would."""
    entry = er.async_get(hass).async_get_or_create("sensor", "bthome", f"{mac}-{key}")
    hass.states.async_set(entry.entity_id, state, {ATTR_UNIT_OF_MEASUREMENT: unit} if unit else {})
    return entry.entity_id
