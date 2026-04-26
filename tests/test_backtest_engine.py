import pandas as pd
import pytest

from backtest.backtest_engine import BacktestEngine
from execution.risk_manager import RiskManager
from strategy.trend_strategy import StrategyConfig, TrendBreakoutStrategy


def build_engine() -> BacktestEngine:
    strategy = TrendBreakoutStrategy(
        config=StrategyConfig(
            min_average_volume=1000,
            breakout_buffer_pct=0.001,
        )
    )
    risk_manager = RiskManager(
        risk_per_trade=0.005,
        max_daily_loss=0.02,
        max_consecutive_losses=3,
    )
    return BacktestEngine(
        strategy=strategy,
        risk_manager=risk_manager,
        initial_capital=100000,
    )


def build_breakout_candles(exit_high: float, exit_low: float) -> pd.DataFrame:
    rows = []
    for index in range(25):
        base = 100 + index
        rows.append(
            {
                "open": base - 0.5,
                "high": base + 1,
                "low": base - 1,
                "close": base,
                "volume": 1000,
            }
        )
    rows.append({"open": 126, "high": 132, "low": 125, "close": 131, "volume": 2500})
    rows.append(
        {
            "open": 132,
            "high": exit_high,
            "low": exit_low,
            "close": 132,
            "volume": 1200,
        }
    )
    return pd.DataFrame(rows)


def test_backtest_records_winning_trade_when_target_is_hit() -> None:
    engine = build_engine()

    result = engine.run("RELIANCE", build_breakout_candles(exit_high=143, exit_low=130))

    assert result.total_trades == 1
    assert result.winning_trades == 1
    assert result.losing_trades == 0
    assert result.win_rate == 1
    assert result.total_pnl == 996
    assert result.final_capital == 100996
    assert result.trades[0].exit_reason == "TARGET"


def test_backtest_records_losing_trade_when_stop_is_hit() -> None:
    engine = build_engine()

    result = engine.run("RELIANCE", build_breakout_candles(exit_high=132, exit_low=125))

    assert result.total_trades == 1
    assert result.winning_trades == 0
    assert result.losing_trades == 1
    assert result.total_pnl == -498
    assert result.final_capital == 99502
    assert result.max_drawdown_pct == pytest.approx(0.00498)
    assert result.trades[0].exit_reason == "STOP_LOSS"


def test_backtest_handles_no_trade_dataset() -> None:
    engine = build_engine()
    candles = pd.DataFrame(
        [
            {
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "volume": 1000,
            }
            for _ in range(30)
        ]
    )

    result = engine.run("FLAT", candles)

    assert result.total_trades == 0
    assert result.total_pnl == 0
    assert result.final_capital == 100000
    assert result.win_rate == 0
    assert result.equity_curve == [100000]
