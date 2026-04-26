import pandas as pd

from config.settings import settings
from execution.risk_manager import RiskManager
from strategy.trend_strategy import TrendBreakoutStrategy


def build_demo_candles() -> pd.DataFrame:
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
    return pd.DataFrame(rows)


def main() -> None:
    strategy = TrendBreakoutStrategy()
    signal = strategy.generate_signal("RELIANCE", build_demo_candles())
    print(signal)

    if signal.entry_price and signal.stop_loss:
        risk_manager = RiskManager(
            risk_per_trade=settings.risk_per_trade,
            max_daily_loss=settings.max_daily_loss,
            max_consecutive_losses=settings.max_consecutive_losses,
        )
        position = risk_manager.calculate_position_size(
            capital=100000,
            entry_price=signal.entry_price,
            stop_loss=signal.stop_loss,
        )
        print(position)


if __name__ == "__main__":
    main()
