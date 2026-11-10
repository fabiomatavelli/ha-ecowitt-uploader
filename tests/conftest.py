"""Shared pytest fixtures for the Ecowitt.net Uploader test suite."""

from __future__ import annotations

import pytest

pytest_plugins = "pytest_homeassistant_custom_component"

MAC = "AA:BB:CC:DD:EE:FF"
# upper(md5(MAC)), computed independently
PASSKEY = "6393CFC4AB6D416690B21278957AEAB2"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Make custom_components discoverable in every test."""
