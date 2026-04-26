import json

import pandas as pd

from backtest.backtest_engine import BacktestResult, BacktestTrade
from backtest.report_exporter import BacktestReportExporter
from strategy.trend_strategy import SignalType


def build_result() -> BacktestResult:
    return BacktestResult(
        initial_capital=100000,
        final_capital=100996,
        total_pnl=996,
        total_trades=1,
        winning_trades=1,
        losing_trades=0,
        win_rate=1.0,
        max_drawdown_pct=0.0,
        average_reward_risk=2.0,
        hold_signals=5,
        trades=[
            BacktestTrade(
                symbol="RELIANCE",
                trade_type=SignalType.BUY,
                entry_index=25,
                exit_index=26,
                entry_price=131,
                exit_price=143,
                stop_loss=125,
                target_price=143,
                quantity=83,
                pnl=996,
                exit_reason="TARGET",
            )
        ],
        equity_curve=[100000, 100996],
    )


def test_exporter_writes_metrics_trades_and_equity_curve(tmp_path) -> None:
    paths = BacktestReportExporter().export(build_result(), tmp_path)

    assert set(paths) == {"metrics", "trades", "equity_curve"}
    assert paths["metrics"].exists()
    assert paths["trades"].exists()
    assert paths["equity_curve"].exists()

    metrics = json.loads(paths["metrics"].read_text(encoding="utf-8"))
    assert metrics["final_capital"] == 100996
    assert metrics["total_trades"] == 1

    trades = pd.read_csv(paths["trades"])
    assert trades.iloc[0]["symbol"] == "RELIANCE"
    assert trades.iloc[0]["trade_type"] == "BUY"

    equity_curve = pd.read_csv(paths["equity_curve"])
    assert list(equity_curve["equity"]) == [100000, 100996]
