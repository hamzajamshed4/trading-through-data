from trading_through_data.agent.features import Features
from trading_through_data.agent.policy import IndicatorPolicy, Signal


def _features(**kw):
    base = dict(close=100.0, sma_fast=100.0, sma_slow=100.0, rsi=50.0, atr=1.0, momentum=0.0, ready=True)
    base.update(kw)
    return Features(**base)


def test_warmup_returns_hold():
    policy = IndicatorPolicy()
    d = policy.decide(_features(ready=False))
    assert d.signal is Signal.HOLD
    assert d.confidence == 0.0


def test_strong_uptrend_triggers_buy():
    policy = IndicatorPolicy()
    f = _features(sma_fast=110.0, sma_slow=100.0, momentum=0.05, rsi=55.0, atr=1.0)
    d = policy.decide(f, has_position=False)
    assert d.signal is Signal.BUY
    assert d.score > 0
    assert 0.0 < d.confidence <= 1.0


def test_strong_downtrend_triggers_sell():
    policy = IndicatorPolicy()
    f = _features(sma_fast=90.0, sma_slow=100.0, momentum=-0.05, rsi=45.0, atr=1.0)
    d = policy.decide(f, has_position=False)
    assert d.signal is Signal.SELL
    assert d.score < 0


def test_long_position_closes_when_conviction_fades():
    policy = IndicatorPolicy()
    f = _features(sma_fast=100.1, sma_slow=100.0, momentum=0.0, rsi=50.0, atr=1.0)
    d = policy.decide(f, has_position=True, position_side="buy")
    assert d.signal in (Signal.CLOSE, Signal.HOLD)


def test_reasons_are_populated():
    policy = IndicatorPolicy()
    d = policy.decide(_features(sma_fast=110.0, sma_slow=100.0, momentum=0.05))
    assert d.reasons and all(isinstance(r, str) for r in d.reasons)
