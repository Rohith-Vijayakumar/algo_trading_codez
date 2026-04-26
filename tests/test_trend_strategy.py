import pandas as pd

from strategy.trend_strategy import SignalType, StrategyConfig, TrendBreakoutStrategy


def build_uptrend_candles(
    breakout_close: float = 131,
    latest_volume: float = 2500,
    base_volume: float = 1000,
) -> pd.DataFrame:
    rows = []
    for index in range(25):
        base = 100 + index
        rows.append(
            {
                "open": base - 0.5,
                "high": base + 1,
                "low": base - 1,
                "close": base,
                "volume": base_volume,
            }
        )
    rows.append(
        {
            "open": breakout_close - 5,
            "high": breakout_close + 1,
            "low": breakout_close - 6,
            "close": breakout_close,
            "volume": latest_volume,
        }
    )
    return pd.DataFrame(rows)


def test_generates_buy_signal_on_volume_breakout() -> None:
    candles = build_uptrend_candles()

    strategy = TrendBreakoutStrategy()
    signal = strategy.generate_signal("RELIANCE", candles)

    assert signal.signal == SignalType.BUY
    assert signal.symbol == "RELIANCE"
    assert signal.entry_price == 131


def test_holds_when_breakout_buffer_is_not_cleared() -> None:
    candles = build_uptrend_candles(breakout_close=125.05)
    strategy = TrendBreakoutStrategy(
        config=StrategyConfig(breakout_buffer_pct=0.002, min_average_volume=1000)
    )

    signal = strategy.generate_signal("RELIANCE", candles)

    assert signal.signal == SignalType.HOLD
    assert signal.reason == "No confirmed setup"


def test_holds_when_average_volume_is_too_low() -> None:
    candles = build_uptrend_candles(base_volume=500, latest_volume=2000)
    strategy = TrendBreakoutStrategy(
        config=StrategyConfig(min_average_volume=1000)
    )

    signal = strategy.generate_signal("THIN", candles)

    assert signal.signal == SignalType.HOLD
    assert signal.reason == "Average volume below liquidity threshold"
