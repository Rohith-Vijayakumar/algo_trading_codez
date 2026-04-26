from backtest.backtest_engine import BacktestResult
from run_backtest import build_parser, format_result


def test_format_result_outputs_key_metrics() -> None:
    result = BacktestResult(
        initial_capital=100000,
        final_capital=101000,
        total_pnl=1000,
        total_trades=4,
        winning_trades=3,
        losing_trades=1,
        win_rate=0.75,
        max_drawdown_pct=0.02,
        average_reward_risk=2.0,
        hold_signals=12,
    )

    output = format_result(result)

    assert "Backtest Result" in output
    assert "Final Capital: 101000.00" in output
    assert "Total PnL: 1000.00" in output
    assert "Win Rate: 75.00%" in output
    assert "Max Drawdown: 2.00%" in output


def test_parser_accepts_required_backtest_arguments() -> None:
    args = build_parser().parse_args(
        [
            "--file",
            "data/reliance.csv",
            "--symbol",
            "RELIANCE",
            "--capital",
            "200000",
            "--asset-class",
            "equity",
        ]
    )

    assert args.file == "data/reliance.csv"
    assert args.symbol == "RELIANCE"
    assert args.capital == 200000
    assert args.asset_class == "equity"
