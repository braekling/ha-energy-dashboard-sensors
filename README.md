# Energy Dashboard Sensors

A Home Assistant custom integration that exposes the key figures of the built-in
**Energy Dashboard** as regular sensor entities, so they can be used in
automations, templates, history, and custom Lovelace cards.

The dashboard computes its numbers in the frontend from your configured energy
sources and the recorder's long-term statistics — they are not available as
entities anywhere. This integration reproduces the exact same calculations on
the backend and publishes them as sensors.

## Sensors

Six metrics are provided, each for four periods — **today, this week, this
month and this year** — for a total of 24 sensors. Every value resets at the
start of its period, matching the corresponding Energy Dashboard view.

| Metric | Unit | Meaning |
| --- | --- | --- |
| Total consumption | kWh | Total energy consumed by the home |
| Solar production | kWh | PV energy produced |
| Net from grid | kWh | Grid import minus export (negative = net export) |
| Solar self-consumption | % | Share of PV production used in the home (battery-aware) |
| Self-sufficiency | % | Share of home consumption covered without the grid (Autarkiegrad) |
| Low-carbon consumption | % | Share of consumed energy that is CO₂-neutral |

Statistics resolution per period follows the dashboard's own logic (hourly for
today, daily for week/month, monthly for the year), so each sensor stays
consistent with the matching dashboard range.

The source entities (grid, solar, battery, CO₂ signal) are picked up
**automatically** from your existing Energy Dashboard configuration. There is
nothing to map manually.

Low-carbon consumption requires the
[CO2 Signal / Electricity Maps](https://www.home-assistant.io/integrations/co2signal/)
integration to be set up; without it that sensor stays unavailable.

## Installation

### HACS (recommended)

1. In HACS, add this repository as a custom repository (category: *Integration*).
2. Install **Energy Dashboard Sensors**.
3. Restart Home Assistant.
4. Go to **Settings → Devices & Services → Add Integration** and search for
   *Energy Dashboard Sensors*.

### Manual

Copy `custom_components/energy_dashboard_sensors` into your Home Assistant
`config/custom_components` directory and restart.

## Options

The update interval (default 5 minutes) can be changed from the integration's
**Configure** dialog. Values are also refreshed automatically whenever you edit
your Energy Dashboard configuration.

## How the values are calculated

The arithmetic is ported directly from the official Home Assistant frontend
(`src/data/energy.ts` and the energy gauge cards) and the
`energy/fossil_energy_consumption` backend calculation, so the sensor values
stay consistent with what the dashboard shows. Statistics are read at hourly
resolution and aggregated per day; the solar self-consumption figure tracks
solar energy through the battery in last-in/first-out order, exactly like the
dashboard.

## License

MIT
