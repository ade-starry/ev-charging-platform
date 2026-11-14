# SP1 to SP4 local import record

Verified: 2026-10-24 (Asia/Shanghai).

## Provenance

- Repository: https://github.com/ade-starry/ev-charging-platform
- Imported branch: `SP1-data-pipeline-and-forecast`, commit `024fb75`.
- Code imported into `subprojects/sp1-data-forecasting/`.
- Source: City of Boulder municipal EV charging data, CC0 1.0.
- Download endpoint: https://services.arcgis.com/ePKBjXrBZ2vEEgWd/arcgis/rest/services/Electric_Vehicle_Charging_Station_Data/FeatureServer/0
- Raw file: `data/raw/boulder-ev/Boulder_EV_Charging_Station_Data.csv`.
- Retrieved 2026-10-23 UTC; 148,136 session records; 23,276,416 bytes.
- Raw SHA-256: `b70e3576015dde9bb663e8aa29db6811cca0ac732771123dbe25acbf6ed48d43`.
- Source observations span 2018–2023. Source-local timezone: `America/Denver`.

## Generated outputs

`data/processed/sp1-demand-forecast-v1.csv` and its `.meta.json` are consumed
directly by SP4. The baseline CSV and metadata are in the same directory.
Canonical sessions, hourly demand, backtest rows, model metrics and pattern
summaries are in `data/interim/`. Data files are Git-ignored and remain local.

The forecast contains 720 continuous UTC hourly rows, 2023-11-01T08:00:00Z
through 2023-12-01T07:00:00Z. Each of 30 rolling origins predicts 24 hours.
Metadata identifies this as a historical rolling-origin backtest, with
`synthetic: false`; the inputs are observed data and the predictions are model outputs.

Four models were evaluated in this run:

| Model | WAPE |
|---|---:|
| naive_daily | 34.80% |
| naive_weekly | 38.34% |
| hour_of_week_profile | 64.49% |
| ridge (selected) | 32.82% |

Ridge MAE: 9.6502 kWh; RMSE: 12.9212 kWh; R²: 0.7039. Selection and
reporting use this same historical evaluation window; these are not independent
final holdout results. Empirical bounds use backtest residuals and are not
validated prospective confidence guarantees.

## Local integration changes

The original rolling-origin selection could skip an hour across US daylight
saving changes. The latest origin is now anchored to local midnight, with
earlier origins spaced exactly 24 UTC hours apart. Earlier local origin hours
can therefore shift at DST. Spring and autumn regression tests cover this policy.

Forecast/baseline metadata now records the analysis timezone; forecast metadata
also records the historical evaluation role and origin policy. SP4 validates
the input and displays source, period, model, bounds and selectable timezones.

The demand series is US historical data. Vehicle monitoring still uses example
records, and the Chinese CNY cost planner remains independent. No live charger
API, current forecast, US cost calculation, Palo Alto import or SP2/SP5 integration
is claimed by this import. Previously generated Word reports and slides have
not been revised as part of this data import.

## Reproduce

From the repository root using the workspace Python environment:

```powershell
& '..\.venv\Scripts\python.exe' -m pip install -r requirements.txt
# Download only when the raw file is absent; preserve the recorded raw snapshot.
& '..\.venv\Scripts\python.exe' subprojects/sp1-data-forecasting/scripts/fetch_datasets.py --dataset us-boulder-ev
& '..\.venv\Scripts\python.exe' subprojects/sp1-data-forecasting/scripts/run_sp1.py --dataset us-boulder-ev --models naive_daily,naive_weekly,hour_of_week_profile,ridge --forecast-days 30
& '..\.venv\Scripts\python.exe' -m pytest subprojects/sp1-data-forecasting/tests subprojects/sp4-monitoring-dashboard/tests -q
& '..\.venv\Scripts\python.exe' -m streamlit run subprojects/sp4-monitoring-dashboard/dashboard.py
```

The outer workspace's `start.bat` also starts the dashboard. Later downloads
may differ from the raw snapshot recorded here.

## Verification

- 104 SP1/SP4 tests passed, including both DST regressions.
- SP4's strict loader accepted the generated forecast and metadata.
- Exactly 720 continuous hourly rows; real-source flag and source timezone checked.
- Streamlit AppTest rendered six charts with no exceptions or displayed errors.
- Default Denver display and switches to UTC and Asia/Shanghai passed; the demand
  chart retained 720 points and the appropriate axis title.
- Boulder source confirmation appeared; synthetic fallback control was absent.
