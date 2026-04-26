import argparse
from pathlib import Path

from backtest.backtest_engine import BacktestResult, BacktestEngine
from data.market_data import MarketDataLoader
from execution.risk_manager import RiskManager
from strategy.trend_strategy import TrendBreakoutStrategy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a strategy backtest from CSV candles.")
    parser.add_argument("--file", required=True, help="Path to CSV candle data.")
    parser.add_argument("--symbol", required=True, help="Symbol to backtest.")
    parser.add_argument("--capital", type=float, default=100000, help="Initial capital.")
    parser.add_argument(
        "--asset-class",
        choices=["equity", "crypto"],
        default="equity",
        help="Strategy preset to use.",
    )
    parser.add_argument(
        "--risk-per-trade",
        type=float,
        default=0.005,
        help="Fraction of capital risked per trade.",
    )
    parser.add_argument(
        "--max-daily-loss",
        type=float,
        default=0.02,
        help="Daily loss kill-switch threshold.",
    )
    parser.add_argument(
        "--max-consecutive-losses",
        type=int,
        default=3,
        help="Consecutive loss kill-switch threshold.",
    )
    return parser


def run_backtest(
    file_path: str | Path,
    symbol: str,
    capital: float,
    asset_class: str,
    risk_per_trade: float,
    max_daily_loss: float,
    max_consecutive_losses: int,
) -> BacktestResult:
    candles = MarketDataLoader().load_csv(file_path, symbol=symbol)
    strategy = TrendBreakoutStrategy(asset_class=asset_class)
    risk_manager = RiskManager(
        risk_per_trade=risk_per_trade,
        max_daily_loss=max_daily_loss,
        max_consecutive_losses=max_consecutive_losses,
    )
    engine = BacktestEngine(
        strategy=strategy,
        risk_manager=risk_manager,
        initial_capital=capital,
    )
    return engine.run(symbol, candles)


def format_result(result: BacktestResult) -> str:
    lines = [
        "Backtest Result",
        f"Initial Capital: {result.initial_capital:.2f}",
        f"Final Capital: {result.final_capital:.2f}",
        f"Total PnL: {result.total_pnl:.2f}",
        f"Total Trades: {result.total_trades}",
        f"Winning Trades: {result.winning_trades}",
        f"Losing Trades: {result.losing_trades}",
        f"Win Rate: {result.win_rate:.2%}",
        f"Max Drawdown: {result.max_drawdown_pct:.2%}",
        f"Average Reward:Risk: {result.average_reward_risk:.2f}",
        f"Hold Signals: {result.hold_signals}",
    ]
    return "\n".join(lines)


def main() -> None:
    args = build_parser().parse_args()
    result = run_backtest(
        file_path=args.file,
        symbol=args.symbol,
        capital=args.capital,
        asset_class=args.asset_class,
        risk_per_trade=args.risk_per_trade,
        max_daily_loss=args.max_daily_loss,
        max_consecutive_losses=args.max_consecutive_losses,
    )
    print(format_result(result))


if __name__ == "__main__":
    main()
