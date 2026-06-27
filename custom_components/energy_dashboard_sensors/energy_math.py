"""Pure energy calculations ported from the Home Assistant Energy Dashboard.

All functions in this module are side-effect free so they can be unit tested
without a running Home Assistant instance. The arithmetic mirrors the official
frontend implementation in ``src/data/energy.ts`` and the energy gauge cards,
to keep the produced sensor values consistent with the dashboard.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PeriodFlows:
    """Energy flows summed for a single statistics period (e.g. one hour).

    Values are kWh. ``to_grid`` and ``to_battery`` represent energy leaving the
    home (export / charging); ``from_grid``, ``from_battery`` and ``solar``
    represent energy entering the home perspective.
    """

    from_grid: float = 0.0
    to_grid: float = 0.0
    solar: float = 0.0
    to_battery: float = 0.0
    from_battery: float = 0.0


@dataclass
class ConsumptionSplit:
    """Result of routing the flows of a single period to their destinations."""

    used_solar: float = 0.0
    used_grid: float = 0.0
    used_battery: float = 0.0
    used_total: float = 0.0
    grid_to_battery: float = 0.0
    battery_to_grid: float = 0.0
    solar_to_battery: float = 0.0
    solar_to_grid: float = 0.0


def compute_consumption_single(flows: PeriodFlows) -> ConsumptionSplit:
    """Route a single period's flows to consumption / battery / grid.

    Direct port of ``computeConsumptionSingle`` from the HA frontend. The
    consumption priority is:
    Solar -> Battery_In, Solar -> Grid_Out, Battery_Out -> Grid_Out,
    Grid_In -> Battery_In, Solar -> Consumption, Battery_Out -> Consumption,
    Grid_In -> Consumption.
    """
    to_grid = max(flows.to_grid, 0.0)
    to_battery = max(flows.to_battery, 0.0)
    solar = max(flows.solar, 0.0)
    from_grid = max(flows.from_grid, 0.0)
    from_battery = max(flows.from_battery, 0.0)

    used_total = from_grid + solar + from_battery - to_grid - to_battery

    grid_to_battery = 0.0
    used_total_remaining = max(used_total, 0.0)

    # Excess grid input beyond consumption must be charging the battery.
    excess_grid_in_after_consumption = max(
        0.0, min(to_battery, from_grid - used_total_remaining)
    )
    grid_to_battery += excess_grid_in_after_consumption
    to_battery -= excess_grid_in_after_consumption
    from_grid -= excess_grid_in_after_consumption

    # Fill the remainder of the battery input from solar.
    solar_to_battery = min(solar, to_battery)
    to_battery -= solar_to_battery
    solar -= solar_to_battery

    # Solar -> Grid_Out
    solar_to_grid = min(solar, to_grid)
    to_grid -= solar_to_grid
    solar -= solar_to_grid

    # Battery_Out -> Grid_Out
    battery_to_grid = min(from_battery, to_grid)
    from_battery -= battery_to_grid

    # Grid_In -> Battery_In (second pass)
    grid_to_battery_second = min(from_grid, to_battery)
    grid_to_battery += grid_to_battery_second
    from_grid -= grid_to_battery_second

    # Solar -> Consumption
    used_solar = min(used_total_remaining, solar)
    used_total_remaining -= used_solar

    # Battery_Out -> Consumption
    used_battery = min(from_battery, used_total_remaining)
    used_total_remaining -= used_battery

    # Grid_In -> Consumption
    used_grid = min(used_total_remaining, from_grid)

    return ConsumptionSplit(
        used_solar=used_solar,
        used_grid=used_grid,
        used_battery=used_battery,
        used_total=used_total,
        grid_to_battery=grid_to_battery,
        battery_to_grid=battery_to_grid,
        solar_to_battery=solar_to_battery,
        solar_to_grid=solar_to_grid,
    )


@dataclass
class SummedEnergy:
    """Aggregated flows and consumption split across all periods of a day."""

    total_from_grid: float = 0.0
    total_to_grid: float = 0.0
    total_solar: float = 0.0
    total_to_battery: float = 0.0
    total_from_battery: float = 0.0
    total_used: float = 0.0
    has_battery: bool = False
    # Per-period consumption splits, ordered by period start, used for the
    # battery-aware solar self-consumption calculation.
    splits: list[ConsumptionSplit] = field(default_factory=list)


def summarize_day(periods: list[PeriodFlows]) -> SummedEnergy:
    """Aggregate per-period flows into daily totals plus per-period splits."""
    summary = SummedEnergy()
    for flows in periods:
        summary.total_from_grid += max(flows.from_grid, 0.0)
        summary.total_to_grid += max(flows.to_grid, 0.0)
        summary.total_solar += max(flows.solar, 0.0)
        summary.total_to_battery += max(flows.to_battery, 0.0)
        summary.total_from_battery += max(flows.from_battery, 0.0)

        split = compute_consumption_single(flows)
        summary.total_used += split.used_total
        summary.splits.append(split)

    summary.has_battery = (
        summary.total_to_battery > 0.0 or summary.total_from_battery > 0.0
    )
    return summary


def total_home_consumption(summary: SummedEnergy) -> float:
    """Total energy consumed by the home over the day (kWh, clamped to >= 0)."""
    return max(0.0, summary.total_used)


def net_from_grid(summary: SummedEnergy) -> float:
    """Net energy drawn from the grid (kWh). Negative means net export."""
    return summary.total_from_grid - summary.total_to_grid


def self_sufficiency_percent(summary: SummedEnergy) -> float | None:
    """Self-sufficiency (Autarkiegrad) in percent, or None if undefined.

    Port of the self-sufficiency gauge:
    ``(1 - min(1, from_grid / used_total)) * 100``.
    """
    consumption = total_home_consumption(summary)
    if consumption <= 0.0:
        return None
    return (1.0 - min(1.0, summary.total_from_grid / consumption)) * 100.0


def solar_self_consumption_percent(summary: SummedEnergy) -> float | None:
    """Solar self-consumption (PV-Eigenverbrauch) in percent, or None.

    Port of ``calculateSolarConsumedGauge``. Without a battery this is simply
    used_solar / solar. With a battery, solar energy is tracked through the
    battery in last-in/first-out order so charge/discharge does not distort the
    ratio.
    """
    if summary.total_solar <= 0.0:
        return None

    if not summary.has_battery:
        used_solar = sum(split.used_solar for split in summary.splits)
        return (used_solar / summary.total_solar) * 100.0

    solar_consumed = 0.0
    solar_returned = 0.0
    battery_lifo: list[list] = []  # entries: [type, value], type in {"solar","grid"}

    def drain_battery(amount: float) -> tuple[float, str]:
        last = battery_lifo[-1]
        entry_type = last[0]
        if amount >= last[1]:
            energy = last[1]
            battery_lifo.pop()
            return energy, entry_type
        last[1] -= amount
        return amount, entry_type

    for split in summary.splits:
        solar_consumed += split.used_solar
        solar_returned += split.solar_to_grid

        if split.grid_to_battery:
            battery_lifo.append(["grid", split.grid_to_battery])
        if split.solar_to_battery:
            battery_lifo.append(["solar", split.solar_to_battery])

        used_battery = split.used_battery
        while used_battery > 0.0 and battery_lifo:
            energy, entry_type = drain_battery(used_battery)
            if entry_type == "solar":
                solar_consumed += energy
            used_battery -= energy

        battery_to_grid = split.battery_to_grid
        while battery_to_grid > 0.0 and battery_lifo:
            energy, entry_type = drain_battery(battery_to_grid)
            if entry_type == "solar":
                solar_returned += energy
            battery_to_grid -= energy

    total_production = solar_consumed + solar_returned
    if total_production <= 0.0:
        return None
    return (solar_consumed / total_production) * 100.0


def fossil_energy(grid_from_per_period: list[float], co2_percent_per_period: list[float]) -> float:
    """High-carbon (fossil) grid energy in kWh for the day.

    Mirrors the ``energy/fossil_energy_consumption`` websocket calc: for each
    period the grid import is multiplied by the fossil-fuel percentage of the
    grid (from the co2signal "%" entity). Missing percentages assume 100%
    fossil, matching the dashboard behaviour.
    """
    fossil = 0.0
    for index, grid_delta in enumerate(grid_from_per_period):
        percent = co2_percent_per_period[index] if index < len(co2_percent_per_period) else 100.0
        if percent is None:
            percent = 100.0
        fossil += grid_delta * percent / 100.0
    return fossil


def low_carbon_consumption_percent(
    summary: SummedEnergy, fossil_grid_energy: float | None
) -> float | None:
    """Low-carbon consumed energy (CO2-neutraler Strom) in percent, or None.

    Port of the carbon-consumed gauge:
    ``totalEnergyConsumed = from_grid + max(0, solar - to_grid)``;
    ``(1 - fossil / totalEnergyConsumed) * 100``.
    """
    if fossil_grid_energy is None:
        return None
    total_energy_consumed = summary.total_from_grid + max(
        0.0, summary.total_solar - summary.total_to_grid
    )
    if total_energy_consumed <= 0.0:
        return None
    return (1.0 - fossil_grid_energy / total_energy_consumed) * 100.0
