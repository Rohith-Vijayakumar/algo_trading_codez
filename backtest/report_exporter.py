import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from backtest.backtest_engine import BacktestResult


class BacktestReportExporter:
    def export(self, result: BacktestResult, output_dir: str | Path) -> dict[str, Path]:
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)

        metrics_path = path / "metrics.json"
        trades_path = path / "trades.csv"
        equity_curve_path = path / "equity_curve.csv"

        metrics_path.write_text(
            json.dumps(self._metrics_payload(result), indent=2),
            encoding="utf-8",
        )
        self._trades_frame(result).to_csv(trades_path, index=False)
        self._equity_curve_frame(result).to_csv(equity_curve_path, index=False)

        return {
            "metrics": metrics_path,
            "trades": trades_path,
            "equity_curve": equity_curve_path,
        }

    def _metrics_payload(self, result: BacktestResult) -> dict[str, float | int]:
        return {
            "initial_capital": result.initial_capital,
            "final_capital": result.final_capital,
            "total_pnl": result.total_pnl,
            "total_trades": result.total_trades,
            "winning_trades": result.winning_trades,
            "losing_trades": result.losing_trades,
            "win_rate": result.win_rate,
            "max_drawdown_pct": result.max_drawdown_pct,
            "average_reward_risk": result.average_reward_risk,
            "hold_signals": result.hold_signals,
        }

    def _trades_frame(self, result: BacktestResult) -> pd.DataFrame:
        rows = []
        for trade in result.trades:
            row = asdict(trade)
            row["trade_type"] = trade.trade_type.value
            rows.append(row)
        return pd.DataFrame(
            rows,
            columns=[
                "symbol",
                "trade_type",
                "entry_index",
                "exit_index",
                "entry_price",
                "exit_price",
                "stop_loss",
                "target_price",
                "quantity",
                "pnl",
                "exit_reason",
            ],
        )

    def _equity_curve_frame(self, result: BacktestResult) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "step": list(range(len(result.equity_curve))),
                "equity": result.equity_curve,
            }
        )
