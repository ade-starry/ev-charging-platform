"""Run with python -m unittest discover -s tests -v from the SP4 directory."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from charging import candidate_starts, load_ev_data, load_forecast, quote_session, validate_rates


class CostTests(unittest.TestCase):
    start = pd.Timestamp("2026-10-14T18:00:00+08:00")

    def test_shanghai_reference_breakdown(self):
        bill = quote_session(self.start, 7, 4, [0.68]*24, 0.42)
        self.assertAlmostEqual(bill.grid_energy_kwh.sum(), 28)
        self.assertAlmostEqual(bill.electricity_cost_cny.sum(), 19.04)
        self.assertAlmostEqual(bill.service_cost_cny.sum(), 11.76)
        self.assertAlmostEqual(bill.estimated_subtotal_cny.sum(), 30.80)

    def test_partial_interval_crosses_tou_boundary(self):
        rates = [0.57 if 8 <= h < 22 else 0.31 for h in range(24)]
        bill = quote_session(pd.Timestamp("2026-10-14T21:30:00+08:00"), 7, 1.5, rates)
        self.assertEqual(len(bill), 2)
        self.assertAlmostEqual(bill.estimated_subtotal_cny.sum(), 7*.5*.57+7*.31)

    def test_midnight_energy_conservation(self):
        bill = quote_session(pd.Timestamp("2026-10-14T23:30:00+08:00"), 11, 2.25, [1]*24)
        self.assertEqual(len(bill), 3)
        self.assertAlmostEqual(bill.grid_energy_kwh.sum(), 24.75)
        self.assertTrue(bill.timestamp.str.endswith("Z").all())

    def test_utc_input_uses_china_tariff(self):
        rates = [0.57 if 8 <= h < 22 else 0.31 for h in range(24)]
        bill = quote_session(pd.Timestamp("2026-10-14T14:00:00Z"), 7, 1, rates)
        self.assertAlmostEqual(bill.estimated_subtotal_cny.sum(), 2.17)

    def test_unknown_service_is_marked(self):
        bill = quote_session(self.start, 7, 1, [.5]*24)
        self.assertFalse(bill.service_fee_included.any())
        self.assertTrue(bill.service_cny_per_kwh.isna().all())

    def test_zero_duration(self):
        self.assertTrue(quote_session(self.start, 7, 0, [.5]*24).empty)

    def test_nonfinite_and_negative_inputs(self):
        for v in [-1, float("inf"), float("nan")]:
            with self.assertRaises(ValueError): quote_session(self.start, v, 4, [.5]*24)
            with self.assertRaises(ValueError): quote_session(self.start, 7, v, [.5]*24)
            with self.assertRaises(ValueError): quote_session(self.start, 7, 4, [.5]*24, v)

    def test_naive_time_rejected(self):
        with self.assertRaises(ValueError): quote_session(pd.Timestamp("2026-10-14"), 7, 4, [.5]*24)

    def test_tariff_length(self):
        with self.assertRaises(ValueError): validate_rates([.5]*23)

    def test_nonfinite_tariff(self):
        with self.assertRaises(ValueError): validate_rates([float("nan")]*24)

    def test_hebei_equal_energy_shift(self):
        rates = [0.57 if 8 <= h < 22 else 0.31 for h in range(24)]
        options = candidate_starts(self.start, 7, 4, rates, window_hours=12)
        self.assertAlmostEqual(options.iloc[0].estimated_subtotal_cny, 15.96)
        self.assertAlmostEqual(options.estimated_subtotal_cny.min(), 8.68)
        self.assertLessEqual(options.delay_hours.max()+4, 12)

    def test_departure_deadline(self):
        with self.assertRaises(ValueError): candidate_starts(self.start, 7, 4, [.5]*24, window_hours=3)

    def test_zero_power(self):
        self.assertEqual(quote_session(self.start, 0, 4, [.5]*24, .4).estimated_subtotal_cny.sum(), 0)


class InputTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "tests")
        self.path = Path(self.temp.name) / "forecast.csv"
        self.data = pd.DataFrame({"timestamp":["2026-10-14T00:00:00Z", "2026-10-14T01:00:00Z"], "predicted_demand_kwh":[10,12], "lower_bound_kwh":[8,10], "upper_bound_kwh":[12,14]})
        self.meta = {"schema_version":"1.0", "generated_at":"2026-10-14T00:00:00Z", "generated_by":"SP1", "source":"TEST synthetic", "resolution":"1h", "timezone":"UTC", "units":{"predicted_demand_kwh":"kWh"}}

    def tearDown(self):
        self.temp.cleanup()

    def write(self):
        self.data.to_csv(self.path,index=False)
        self.path.with_suffix(".meta.json").write_text(json.dumps(self.meta),encoding="utf-8")

    def test_valid_forecast(self):
        self.write()
        data, meta = load_forecast(self.path)
        self.assertEqual(data.local_time.iloc[0].hour, 8)

    def test_missing_metadata(self):
        self.data.to_csv(self.path,index=False)
        with self.assertRaises(ValueError): load_forecast(self.path)

    def test_invalid_columns(self):
        self.data = pd.DataFrame({"wrong":[1]})
        self.write()
        with self.assertRaises(ValueError): load_forecast(self.path)

    def test_gap(self):
        self.data.loc[1,"timestamp"] = "2026-10-14T02:00:00Z"
        self.write()
        with self.assertRaises(ValueError): load_forecast(self.path)

    def test_duplicate_timestamp(self):
        self.data.loc[1,"timestamp"] = self.data.loc[0,"timestamp"]
        self.write()
        with self.assertRaises(ValueError): load_forecast(self.path)

    def test_invalid_bounds(self):
        self.data.loc[0,"lower_bound_kwh"] = 15
        self.write()
        with self.assertRaises(ValueError): load_forecast(self.path)

    def test_bad_units(self):
        self.meta["units"] = {"predicted_demand_kwh":"kW"}
        self.write()
        with self.assertRaises(ValueError): load_forecast(self.path)

    def test_nonfinite_demand(self):
        self.data["predicted_demand_kwh"] = self.data["predicted_demand_kwh"].astype(float)
        self.data.loc[0,"predicted_demand_kwh"] = float("inf")
        self.write()
        with self.assertRaises(ValueError): load_forecast(self.path)

    def test_empty_csv(self):
        self.write()
        self.path.write_text("",encoding="utf-8")
        with self.assertRaises(ValueError): load_forecast(self.path)

    def test_demo_snapshot(self):
        data = load_ev_data(ROOT / "assets/demo_ev_snapshot.csv")
        self.assertAlmostEqual(data.Power_kW.sum(),54.6)

    def test_bad_soc(self):
        path = Path(self.temp.name)/"ev.csv"
        pd.DataFrame({"EV_ID":["EV1"],"SOC":[101],"Status":["Charging"],"Power_kW":[7]}).to_csv(path,index=False)
        with self.assertRaises(ValueError): load_ev_data(path)

    def test_status_power_conflict(self):
        path = Path(self.temp.name)/"ev.csv"
        pd.DataFrame({"EV_ID":["EV1"],"SOC":[50],"Status":["Waiting"],"Power_kW":[7]}).to_csv(path,index=False)
        with self.assertRaises(ValueError): load_ev_data(path)


if __name__ == "__main__":
    unittest.main()
