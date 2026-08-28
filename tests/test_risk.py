from trading_through_data.agent.features import Features
from trading_through_data.agent.policy import Signal
from trading_through_data.agent.risk import RiskConfig


def _features(close=100.0, atr=2.0):
    return Features(close=close, sma_fast=close, sma_slow=close, rsi=50.0, atr=atr, momentum=0.0, ready=True)


def test_stops_are_atr_based():
    risk = RiskConfig(atr_stop_mult=2.0, atr_take_mult=3.0)
    f = _features(close=100.0, atr=2.0)
    sl, tp = risk.stops(Signal.BUY, f)
    assert sl == 100.0 - 4.0
    assert tp == 100.0 + 6.0
    sl_s, tp_s = risk.stops(Signal.SELL, f)
    assert sl_s == 100.0 + 4.0
    assert tp_s == 100.0 - 6.0


def test_risk_based_volume_scales_with_equity():
    risk = RiskConfig(risk_per_trade=0.02, atr_stop_mult=2.0, contract_size=1.0)
    f = _features(close=100.0, atr=2.0)
    # risk_amount = 10000*0.02 = 200; stop_dist = 4 -> vol = 50
    assert risk.volume(10_000.0, f) == 50.0


def test_fixed_volume_overrides_sizing():
    risk = RiskConfig(fixed_volume=0.01)
    f = _features()
    assert risk.volume(1_000_000.0, f) == 0.01


def test_normalize_snaps_to_step_and_bounds():
    risk = RiskConfig(volume_min=0.01, volume_step=0.01, volume_max=5.0)
    assert risk.normalize_volume(0.017) == 0.02
    assert risk.normalize_volume(0.004) == 0.01   # below min -> min
    assert risk.normalize_volume(999.0) == 5.0     # above max -> max


def test_volume_calibrated_for_gold_like_instrument():
    # XAUUSD-like: contract size 100, ATR 16 on a ~100k account. The notional
    # cap keeps the size sane (0.5 lots) rather than the unbounded ~60 lots the
    # old generic sizing would have produced.
    risk = RiskConfig(
        risk_per_trade=0.02, atr_stop_mult=2.0, contract_size=100.0,
        volume_min=0.01, volume_step=0.01, volume_max=2.0,
    )
    f = _features(close=2000.0, atr=16.0)
    vol = risk.volume(100_000.0, f)
    # risk-based 0.625, notional-capped 0.5 -> min = 0.5, snapped to step.
    assert vol == 0.5
    assert vol <= risk.volume_max
