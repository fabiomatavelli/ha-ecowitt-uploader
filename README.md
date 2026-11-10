# Ecowitt.net Uploader for Home Assistant

Upload the readings of **any** weather station in Home Assistant to your station on [ecowitt.net](https://www.ecowitt.net) — no Ecowitt gateway needed.

Your station can be anything Home Assistant already knows about (Shelly, BTHome, Zigbee, ESPHome, a template sensor...): you pick which sensor is the temperature, the wind, the rain and so on, and the integration sends the current values to Ecowitt.net with the Ecowitt protocol at a fixed interval, converting units as needed.

> This is a community project. It is not affiliated with or endorsed by Ecowitt, and Ecowitt.net may change its upload service at any time.

## Requirements

- Home Assistant 2026.3 or newer.
- An [ecowitt.net](https://www.ecowitt.net) account.

## 1. Add your station on ecowitt.net

1. Sign in to ecowitt.net and add a new device.
2. Set **Device Type** to **Weather Station**.
3. Enter a **MAC address** for it and save. If your station has a MAC address of its own (e.g. its Bluetooth address, shown on its device page in Home Assistant), use that one; otherwise any unique address works, such as a locally administered one like `02:12:34:56:78:9A`.

Write the MAC address down: the integration uses it to identify your station, so it must be exactly the one you entered here.

## 2. Install the integration

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=fabiomatavelli&repository=ha-ecowitt-uploader&category=integration)

Or, in HACS, add `https://github.com/fabiomatavelli/ha-ecowitt-uploader` as a custom repository (type **Integration**), install **Ecowitt.net Uploader** and restart Home Assistant.

Manual install: copy `custom_components/ecowitt_uploader` into your `config/custom_components/` folder and restart.

## 3. Configure

**Settings** > **Devices & services** > **Add integration** > **Ecowitt.net Uploader**:

1. Enter the station's **MAC address** (any common format is accepted) and the **upload interval** (30-600 seconds, 60 by default).
2. Map your sensors. Leave a measurement empty if your station doesn't have it; at least one is required.

You can change the interval and the mapping later from the integration's **Configure** button.

### Measurements and units

Units are converted automatically from the sensor's own unit of measurement, so metric and imperial sensors both work. A sensor whose unit can't be converted is skipped.

| Measurement | Accepted units |
| --- | --- |
| Outdoor / indoor temperature | °C, °F, K |
| Outdoor / indoor humidity | % |
| Absolute / relative pressure | hPa, mbar, kPa, Pa, inHg, mmHg, psi |
| Wind speed, wind gust | km/h, m/s, mph, kn, ft/s, Beaufort |
| Wind direction | ° |
| Rain rate | mm/h, in/h, mm/d, in/d |
| Rain event / last hour / today / week / month / year | mm, cm, in |
| Solar radiation | W/m² or lx |
| UV index | (no unit) |

**Relative pressure:** if you don't map a sea-level pressure sensor, it's calculated from the absolute pressure and the **elevation** set in Home Assistant (**Settings** > **System** > **General**), so make sure that's correct.

**Rain totals:** many stations only report a running total. Home Assistant's [Utility Meter](https://www.home-assistant.io/integrations/utility_meter/) helper turns it into daily, weekly, monthly and yearly totals you can map here.

## Status sensor

Each station gets a **Last upload** diagnostic sensor with the time of the last upload Ecowitt.net accepted, and a `fields` attribute listing what was sent. It becomes unavailable while uploads are failing; the reason is in the Home Assistant log.

## Removal

**Settings** > **Devices & services** > **Ecowitt.net Uploader** > ⋮ > **Delete**. Uploads stop immediately; the data already on ecowitt.net stays there.

## License

[MIT](LICENSE)
