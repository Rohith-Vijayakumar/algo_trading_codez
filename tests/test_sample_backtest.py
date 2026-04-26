from pathlib import Path

from run_backtest import format_result, run_backtest


def test_sample_reliance_backtest_runs_end_to_end() -> None:
    sample_file = Path("sample_data/reliance_sample.csv")

    result = run_backtest(
        file_path=sample_file,
        symbol="RELIANCE",
        capital=100000,
        asset_class="equity",
        risk_per_trade=0.005,
        max_daily_loss=0.02,
        max_consecutive_losses=3,
    )

    assert result.total_trades == 1
    assert result.total_pnl == 996
    assert result.final_capital == 100996
    assert result.trades[0].exit_reason == "TARGET"
    assert "Backtest Result" in format_result(result)
