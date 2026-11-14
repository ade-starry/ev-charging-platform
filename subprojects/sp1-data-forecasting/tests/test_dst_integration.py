"""Fixed 24-hour prediction windows must not lose data at US DST changes."""
import numpy as np
import pandas as pd
import pytest
from sp1.pipeline import build_feature_frame
from sp1.models import build_models, rolling_backtest


@pytest.mark.parametrize('start', ['2023-09-25T00:00:00Z', '2024-01-29T00:00:00Z'])
def test_fixed_horizons_cross_denver_dst_without_gaps(start):
    timestamps = pd.date_range(start, periods=60 * 24, freq='h')
    frame = pd.DataFrame({'timestamp': timestamps, 'demand_kwh': 20 + np.arange(len(timestamps)) % 24})
    features = build_feature_frame(frame, local_tz='America/Denver')
    result = rolling_backtest(features, build_models()['naive_daily'], horizon=24,
                              step=24, min_train_intervals=14 * 24, n_origins=30,
                              origin_hour_local=0, local_tz='America/Denver')
    predicted = result.predictions
    assert len(predicted) == 720
    assert predicted.timestamp.is_unique
    assert (predicted.timestamp.diff().dropna() == pd.Timedelta(hours=1)).all()
    origins = pd.DatetimeIndex(predicted.origin.unique())
    assert origins[-1].tz_convert('America/Denver').hour == 0
    assert len(set(origins.tz_convert('America/Denver').hour)) == 2
    assert (predicted.timestamp > predicted.origin).all()
