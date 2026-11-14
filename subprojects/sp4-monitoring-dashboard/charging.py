"""Pure validation and auditable charging estimates in kW, kWh and CNY."""
import json
import math
from pathlib import Path
import pandas as pd

LOCAL_TZ = "Asia/Shanghai"


def finite_nonnegative(value, label):
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"{label} must be finite and non-negative.")
    return number


def validate_rates(rates):
    """Validate a complete 24-hour electricity tariff in CNY per grid kWh."""
    if len(rates) != 24:
        raise ValueError("A tariff must contain exactly 24 hourly rates.")
    return [finite_nonnegative(v, "Electricity rate") for v in rates]


def quote_session(start, power_kw, duration_hours, rates, service_cny_per_kwh=None):
    """Estimate grid kWh and CNY at constant grid-side power.

    Start must be timezone aware. Tariffs apply in China local time. Hour
    boundaries split partial intervals and midnight correctly. An unknown
    service fee means electricity-only, not a verified free service.
    """
    rates = validate_rates(rates)
    power = finite_nonnegative(power_kw, "Power")
    duration = finite_nonnegative(duration_hours, "Duration")
    if duration > 168:
        raise ValueError("Estimates are limited to seven days.")
    cursor = pd.Timestamp(start)
    if cursor.tzinfo is None:
        raise ValueError("Session start must include a timezone.")
    cursor = cursor.tz_convert(LOCAL_TZ)
    end = cursor + pd.Timedelta(hours=duration)
    fee = 0 if service_cny_per_kwh is None else finite_nonnegative(service_cny_per_kwh, "Service fee")
    columns = ["timestamp", "local_start", "duration_hours", "grid_energy_kwh", "electricity_cny_per_kwh", "service_cny_per_kwh", "electricity_cost_cny", "service_cost_cny", "estimated_subtotal_cny", "service_fee_included"]
    rows = []
    while cursor < end:
        stop = min(cursor.floor("h") + pd.Timedelta(hours=1), end)
        hours = (stop - cursor).total_seconds() / 3600
        energy = power * hours
        rate = rates[cursor.hour]
        rows.append([cursor.tz_convert("UTC").isoformat().replace("+00:00", "Z"), cursor.isoformat(), hours, energy, rate, fee if service_cny_per_kwh is not None else None, energy * rate, energy * fee, energy * (rate + fee), service_cny_per_kwh is not None])
        cursor = stop
    return pd.DataFrame(rows, columns=columns)


def candidate_starts(start, power_kw, duration_hours, rates, fee=None, window_hours=24):
    """Compare equal-energy starts inside a connection window, without fleet control.

    Sample delays every 30 minutes, including the final feasible departure.
    """
    duration = finite_nonnegative(duration_hours, "Duration")
    window = finite_nonnegative(window_hours, "Connection window")
    if window > 168 or duration > window:
        raise ValueError("Charging must fit within a window of at most seven days.")
    latest = window - duration
    delays = sorted(set([i / 2 for i in range(int(latest * 2) + 1)] + [latest]))
    rows = []
    for delay in delays:
        candidate = pd.Timestamp(start) + pd.Timedelta(hours=delay)
        bill = quote_session(candidate, power_kw, duration, rates, fee)
        rows.append({"start": candidate, "delay_hours": delay, "estimated_subtotal_cny": float(bill.estimated_subtotal_cny.sum())})
    return pd.DataFrame(rows)


def load_ev_data(path):
    """Read snapshot CSV: EV_ID, SOC percent, Status and Power_kW."""
    data = pd.read_csv(path)
    required = ["EV_ID", "SOC", "Status", "Power_kW"]
    if not set(required).issubset(data.columns) or data.empty:
        raise ValueError("Snapshot requires non-empty EV_ID, SOC, Status and Power_kW columns.")
    if data[required].isna().any().any() or data.EV_ID.duplicated().any():
        raise ValueError("Snapshot has missing values or duplicate IDs.")
    data["EV_ID"] = data.EV_ID.astype(str)
    for column in ["SOC", "Power_kW"]:
        data[column] = pd.to_numeric(data[column], errors="raise")
        if not data[column].map(math.isfinite).all():
            raise ValueError(f"{column} contains non-finite values.")
    if not data.SOC.between(0, 100).all() or (data.Power_kW < 0).any():
        raise ValueError("SOC must be 0–100%; power must be non-negative.")
    if not data.Status.isin(["Charging", "Waiting", "Complete", "Offline"]).all():
        raise ValueError("Unsupported vehicle status.")
    if ((data.Status != "Charging") & (data.Power_kW != 0)).any():
        raise ValueError("A non-charging vehicle has positive power.")
    return data


def load_forecast(path):
    """Validate SP1 hourly UTC energy (kWh) and sibling metadata before display."""
    path = Path(path)
    meta_path = path.with_suffix(".meta.json")
    if not meta_path.exists():
        raise ValueError("Forecast metadata is missing: " + meta_path.name)
    meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
    if not isinstance(meta, dict) or not isinstance(meta.get("units"), dict):
        raise ValueError("Forecast metadata must be an object with a units object.")
    for field, expected in {"schema_version": "1.0", "generated_by": "SP1", "resolution": "1h", "timezone": "UTC"}.items():
        if meta.get(field) != expected:
            raise ValueError(f"Forecast metadata {field} must be {expected}.")
    if not meta.get("source") or not meta.get("generated_at") or meta.get("units", {}).get("predicted_demand_kwh") != "kWh":
        raise ValueError("Metadata must declare source, generation time and kWh units.")
    generated = pd.Timestamp(meta["generated_at"])
    if pd.isna(generated) or generated.tzinfo is None or generated.utcoffset().total_seconds() != 0:
        raise ValueError("Metadata generation time must be UTC.")
    data = pd.read_csv(path)
    columns = ["timestamp", "predicted_demand_kwh", "lower_bound_kwh", "upper_bound_kwh"]
    if data.empty or not set(columns).issubset(data.columns):
        raise ValueError("Forecast is empty or required columns are missing.")
    if not data.timestamp.astype(str).str.endswith("Z").all():
        raise ValueError("Forecast timestamps must end in Z (UTC).")
    data["timestamp"] = pd.to_datetime(data.timestamp, utc=True, errors="raise")
    if not (data.timestamp == data.timestamp.dt.floor("h")).all() or data.timestamp.duplicated().any():
        raise ValueError("Timestamps must be unique whole-hour boundaries.")
    data = data.sort_values("timestamp").reset_index(drop=True)
    if len(data) > 1 and not (data.timestamp.diff().dropna() == pd.Timedelta(hours=1)).all():
        raise ValueError("Forecast contains missing hourly intervals.")
    for column in columns[1:]:
        data[column] = pd.to_numeric(data[column], errors="raise")
        values = data[column].dropna()
        if (column == "predicted_demand_kwh" and data[column].isna().any()) or not values.map(math.isfinite).all() or (values < 0).any():
            raise ValueError(f"{column} must contain finite non-negative values.")
    if (data.lower_bound_kwh > data.predicted_demand_kwh).any() or (data.upper_bound_kwh < data.predicted_demand_kwh).any():
        raise ValueError("Confidence bounds do not bracket demand.")
    data["local_time"] = data.timestamp.dt.tz_convert(LOCAL_TZ)
    return data, meta


def demo_forecast(day):
    """Synthetic view example, not an ML prediction or observed demand."""
    local = pd.date_range(pd.Timestamp(day, tz=LOCAL_TZ), periods=24, freq="h")
    demand = [20, 18, 17, 16, 18, 25, 35, 50, 65, 78, 82, 75, 68, 65, 70, 85, 95, 110, 125, 118, 100, 80, 55, 35]
    return pd.DataFrame({"local_time": local, "predicted_demand_kwh": demand})
