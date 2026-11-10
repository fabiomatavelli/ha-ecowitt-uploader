"""Station recognition from Shelly manufacturer data."""

from __future__ import annotations

import pytest

from custom_components.ecowitt_uploader.profiles import WS90, parse_shelly_model_id, profile_for

from .conftest import WS90_MANUFACTURER_DATA


def test_ws90_is_recognised() -> None:
    assert parse_shelly_model_id(WS90_MANUFACTURER_DATA) == 0x000B
    assert profile_for(WS90_MANUFACTURER_DATA) is WS90


def test_block_order_does_not_matter() -> None:
    data = {0x0BA9: bytes.fromhex("0affeeddccbbaa" + "0b0b00" + "010100")}
    assert parse_shelly_model_id(data) == 0x000B


@pytest.mark.parametrize(
    "data",
    [
        {},  # no Shelly data
        {0x0001: bytes.fromhex("0b0b00")},  # another company
        {0x0BA9: bytes.fromhex("010100")},  # no model block
        {0x0BA9: bytes.fromhex("0b0b")},  # truncated model
        {0x0BA9: bytes.fromhex("ff0b0b00")},  # unknown block first
    ],
)
def test_unrecognised_data(data: dict[int, bytes]) -> None:
    assert parse_shelly_model_id(data) is None
    assert profile_for(data) is None


def test_other_shelly_model_is_not_supported() -> None:
    button = {0x0BA9: bytes.fromhex("0101000b0100")}  # model 0x0001: BLU Button
    assert parse_shelly_model_id(button) == 0x0001
    assert profile_for(button) is None
