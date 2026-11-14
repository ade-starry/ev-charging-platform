# SP4 — Charging Monitoring and Visualisation Platform

**Owner:** Li Chunren (李春仁)
**Consumes:** SP1 forecast, SP2 schedule, SP3 solar, SP5 assessment
**Produces:** the user-facing dashboard — the thing people actually see

## Tasks (from the official brief)
- Design a charging monitoring architecture.
- Develop a software dashboard to display charging status, energy consumption, and charging costs.
- Implement data visualisation and reporting functions.

## Recommended stack (from the supervisor)
Python (Dash / Streamlit) **or** React / Node.js, paired with a lightweight database
(SQLite / PostgreSQL).

## Suggested views
Real-time charging status · predicted demand vs actual · cost savings · environmental impact

## Output contract
Consumes every other subsystem's output file. Read `docs/integration-contract.md` in full —
you are the integration point, so you will find interface bugs before anyone else does.

## Layout
```
dashboard.py      # Streamlit views and interaction
charging.py       # pure calculations and input validation
assets/           # clearly labelled example snapshot and sourced tariffs
tests/            # boundary and malformed-input checks
```

## Run the current prototype

From the repository root, activate your Python environment and run:

```powershell
pip install -r requirements.txt
python -m streamlit run subprojects/sp4-monitoring-dashboard/dashboard.py
```

The outer workspace's `start.bat` uses its existing `.venv` and changes into
the repository so `.streamlit/config.toml` supplies the light theme.

The dashboard provides vehicle SOC/status charts, an hourly demand preview,
instant charging-cost estimates, feasible start-time comparisons, regional
price evidence and integration-readiness information. Monitoring reloads the
example CSV every 15 seconds during an active browser session. This is not
live charger telemetry. Missing SP1 data leaves the other views available;
an optional synthetic curve is explicitly labelled. Invalid supplied SP1
data is rejected rather than replaced with a fake forecast.

## Cost model and sources

Energy is grid-side power (kW) multiplied by duration (hours). The estimate
splits partial sessions at each China local hour boundary, including midnight,
and sums energy times electricity and optional service prices. UTC timestamps
are retained in the exported calculation; price lookup uses Asia/Shanghai.
An unknown service fee produces an **electricity-only** subtotal. Parking,
idle fees, discounts, battery capacity/taper and charging losses are excluded.

`assets/regional_tariffs.json` records six regional contexts researched on
2026-10-14: Shanghai, Beijing, Shijiazhuang/Hebei, Zhejiang, Shenzhen and
Chengdu/Sichuan. Four have numerical reference profiles; Shenzhen and Sichuan
require station prices. Every entry contains its source, date, scope and
limitations. Shanghai is a **2024 historical public-network average**, not a
2026 station quote. Residential tariffs must not be applied to commercial
fast-charging stations. Zhejiang's official pages timed out during research;
the notice text and an official power-company FAQ corroborate its values.

No live operator pricing API is connected. Input changes recalculate
immediately against these references or user-entered prices. Station mode
supports a flat price or an editable 24-hour electricity schedule. Enter an
applicable service fee separately and confirm the station prices before use.
The start comparison samples half-hour delays, preserves energy and enforces
the stated connection deadline. It does not replace SP2 fleet optimisation.

## Verification

From this SP4 directory:

```powershell
python -m unittest discover -s tests -v
```

25 tests cover known arithmetic totals, midnight/partial intervals, timezone
conversion, invalid inputs, departure limits and SP1 metadata/schema errors.
On 2026-10-14 Streamlit AppTest rendered six charts without exceptions and
verified switching among published references and station-specific mode.
The local reference example is 7 kW for four hours: Shanghai's historical
subtotal is CNY 30.80; Hebei's electricity-only cost is CNY 15.96 at 18:00
versus CNY 8.68 at 22:00 (same 28 kWh, sufficient connection time).

## SP1 integration completed locally (2026-10-24)

The dashboard now reads the generated Boulder forecast from
`data/processed/sp1-demand-forecast-v1.csv` and its sibling metadata.
148,136 historical charging sessions produce 720 hourly predictions from
2023-11-01 08:00 UTC through 2023-12-01 07:00 UTC. These are rolling-origin
historical backtest predictions, not a current operational forecast.

The chart defaults to America/Denver, offers UTC and Asia/Shanghai, displays
source/model/interval metadata, and provides CSV download. Vehicle records
remain fictional examples. The Chinese cost planner uses independent inputs
and does not price the Boulder demand series.

See `docs/sp1-sp4-import.md` for provenance and reproduction commands.
On 2026-10-24, all 104 SP1/SP4 tests passed, including spring/autumn DST
regressions. Streamlit AppTest loaded the real forecast, rendered six charts,
and switched all three demand display timezones without errors.

## Remaining integration and validation contract

SP1 metadata must accompany the CSV as `sp1-demand-forecast-v1.meta.json`.
Schema 1.0, SP1, UTC, 1h, source, generation time and kWh units are checked.
Timestamp gaps, duplicates, non-finite demand and inconsistent bounds are
rejected. A short valid preview is allowed with a warning about the SP2
30-day requirement. SP2/SP3/SP5 rendering is planned; their file presence
alone does not certify validation or completed integration.
