# Ecowitt.net Uploader for Home Assistant

Upload your **Ecowitt** weather station to [ecowitt.net](https://www.ecowitt.net) straight from Home Assistant, over Bluetooth — no Ecowitt gateway needed.

Some Ecowitt stations, like the WS90 sold by Shelly, broadcast their readings over Bluetooth (BTHome) instead of talking to an Ecowitt gateway, so they never reach ecowitt.net on their own. This integration finds the station, reads it through Home Assistant's BTHome integration and uploads its readings to your station on ecowitt.net with the Ecowitt protocol.

Only supported Ecowitt stations can be added: the station is recognised from its Bluetooth advertisement and identified on ecowitt.net by its own Bluetooth address, so there's nothing to map or type by hand.

> This is a community project. It is not affiliated with or endorsed by Ecowitt or Shelly, and Ecowitt.net may change its upload service at any time.

## Supported stations

| Station | Readings uploaded | Notes |
| --- | --- | --- |
| Ecowitt WS90 (Shelly SBWS-90CM) | Temperature, humidity, absolute and relative pressure, wind speed, gust and direction, solar radiation, UV index, rain (rate, daily, weekly, monthly, yearly) | Rain totals and rate are calculated from the station's accumulated rain (see below). |

Your station isn't listed? Open an issue with its model and the diagnostics of its BTHome device.

## Requirements

- Home Assistant 2026.3 or newer, with Bluetooth (a local adapter or a Bluetooth proxy) in range of the station.
- The station added to Home Assistant's **BTHome** integration (Home Assistant usually discovers it on its own).
- An [ecowitt.net](https://www.ecowitt.net) account.

## Installation

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=fabiomatavelli&repository=ha-ecowitt-uploader&category=integration)

Or, in HACS, add `https://github.com/fabiomatavelli/ha-ecowitt-uploader` as a custom repository (type **Integration**), install **Ecowitt.net Uploader** and restart Home Assistant.

Manual install: copy `custom_components/ecowitt_uploader` into your `config/custom_components/` folder and restart.

## Setup

1. Home Assistant discovers the station and offers **Ecowitt.net Uploader** under **Settings** > **Devices & services**. You can also add it yourself with **Add integration** > **Ecowitt.net Uploader**.
2. The setup dialog shows the station's **MAC address**. Sign in to ecowitt.net, add a new device with **Device Type: Weather Station** and that exact MAC address.
3. Back in Home Assistant, confirm. Readings are uploaded every 60 seconds; change the interval (30-600 s) with the integration's **Configure** button.

## How readings are uploaded

- Units are converted from whatever Home Assistant shows (e.g. °C, km/h, hPa, lux) to the ones the Ecowitt protocol uses.
- **Relative pressure** is calculated from the station's absolute pressure and the **elevation** set in Home Assistant (**Settings** > **System** > **General**), so make sure that's correct.
- **Rain:** the WS90 only reports an ever-growing rain total. The integration keeps track of where each day, week (starting on Sunday), month and year began and uploads the difference, plus a rain rate from the last 10 minutes. Totals start at zero when the integration is first set up and survive restarts.

## Status sensor

Each station gets a **Last upload** diagnostic sensor with the time of the last upload Ecowitt.net accepted, and a `fields` attribute listing what was sent. It becomes unavailable while uploads are failing; the reason is in the Home Assistant log.

## Removal

**Settings** > **Devices & services** > **Ecowitt.net Uploader** > ⋮ > **Delete**. Uploads stop immediately; the data already on ecowitt.net stays there.

## License

[MIT](LICENSE)
